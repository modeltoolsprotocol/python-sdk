import click
import pytest

from mtp_sdk.introspect import (
    MTP_SPEC_VERSION,
    _build_command,
    _extract_arg,
    _infer_type,
    _is_filtered_param,
    _walk_commands,
    generate_schema,
)
from mtp_sdk.types import AuthConfig, CommandAnnotation, DescribeOptions


# --- _infer_type ---


class TestInferType:
    def test_flag_option(self):
        @click.command()
        @click.option("--verbose", is_flag=True)
        def cli(verbose):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("boolean", None)

    def test_choice(self):
        @click.command()
        @click.option("--color", type=click.Choice(["red", "green", "blue"]))
        def cli(color):
            pass
        param = cli.params[0]
        mtp_type, values = _infer_type(param)
        assert mtp_type == "enum"
        assert values == ["red", "green", "blue"]

    def test_multiple_option(self):
        @click.command()
        @click.option("--file", multiple=True)
        def cli(file):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("array", None)

    def test_nargs_minus_one(self):
        @click.command()
        @click.argument("files", nargs=-1)
        def cli(files):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("array", None)

    def test_int_type(self):
        @click.command()
        @click.option("--count", type=int)
        def cli(count):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("integer", None)

    def test_int_range(self):
        @click.command()
        @click.option("--port", type=click.IntRange(1, 65535))
        def cli(port):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("integer", None)

    def test_float_type(self):
        @click.command()
        @click.option("--rate", type=float)
        def cli(rate):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("number", None)

    def test_float_range(self):
        @click.command()
        @click.option("--ratio", type=click.FloatRange(0.0, 1.0))
        def cli(ratio):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("number", None)

    def test_bool_type(self):
        @click.command()
        @click.option("--flag", type=bool)
        def cli(flag):
            pass
        param = cli.params[0]
        assert _infer_type(param)[0] == "boolean"

    def test_path_type(self):
        @click.command()
        @click.option("--output", type=click.Path())
        def cli(output):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("path", None)

    def test_count_option(self):
        @click.command()
        @click.option("-v", "--verbose", count=True)
        def cli(verbose):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("integer", None)

    def test_type_override(self):
        @click.command()
        @click.option("--count", type=str)
        def cli(count):
            pass
        param = cli.params[0]
        assert _infer_type(param, {"count": "integer"}) == ("integer", None)

    def test_default_string(self):
        @click.command()
        @click.option("--name")
        def cli(name):
            pass
        param = cli.params[0]
        assert _infer_type(param) == ("string", None)


# --- _is_filtered_param ---


class TestIsFilteredParam:
    def test_hidden_option(self):
        @click.command()
        @click.option("--secret", hidden=True)
        def cli(secret):
            pass
        param = cli.params[0]
        assert _is_filtered_param(param) is True

    def test_help_param(self):
        # Click doesn't add --help to params by default; simulate one
        param = click.Option(["--help"], is_flag=True, help="Show help")
        assert _is_filtered_param(param) is True

    def test_describe_param(self):
        param = click.Option(["--mtp-describe"], is_flag=True)
        assert _is_filtered_param(param) is True

    def test_version_param(self):
        @click.command()
        @click.version_option("1.0.0")
        def cli():
            pass
        version_param = next(p for p in cli.params if p.name == "version")
        assert _is_filtered_param(version_param) is True

    def test_regular_param_not_filtered(self):
        @click.command()
        @click.option("--format", help="Output format")
        def cli(format):
            pass
        param = cli.params[0]
        assert _is_filtered_param(param) is False


# --- _extract_arg ---


class TestExtractArg:
    def test_option_with_long_flag(self):
        @click.command()
        @click.option("--format", help="Output format")
        def cli(format):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.name == "--format"
        assert arg.type == "string"
        assert arg.description == "Output format"

    def test_option_with_short_and_long(self):
        @click.command()
        @click.option("-f", "--format", help="Output format")
        def cli(format):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.name == "--format"

    def test_short_only_option(self):
        @click.command()
        @click.option("-v", is_flag=True, help="Verbose")
        def cli(v):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.name == "-v"

    def test_option_with_default(self):
        @click.command()
        @click.option("--format", default="json", help="Format")
        def cli(format):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.default == "json"

    def test_required_option(self):
        @click.command()
        @click.option("--output", required=True, help="Output path")
        def cli(output):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.required is True

    def test_optional_option(self):
        @click.command()
        @click.option("--output", help="Output path")
        def cli(output):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.required is False

    def test_enum_option(self):
        @click.command()
        @click.option("--color", type=click.Choice(["red", "green", "blue"]))
        def cli(color):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.type == "enum"
        assert arg.values == ["red", "green", "blue"]

    def test_positional_argument(self):
        @click.command()
        @click.argument("input_file")
        def cli(input_file):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.name == "input_file"
        assert arg.type == "string"
        assert arg.required is True

    def test_optional_argument(self):
        @click.command()
        @click.argument("output", required=False)
        def cli(output):
            pass
        param = cli.params[0]
        arg = _extract_arg(param)
        assert arg.required is False

    def test_argument_description_from_annotation(self):
        @click.command()
        @click.argument("input_file")
        def cli(input_file):
            pass
        param = cli.params[0]
        arg = _extract_arg(param, arg_descriptions={"input_file": "Input file path"})
        assert arg.description == "Input file path"

    def test_numeric_default_coercion(self):
        @click.command()
        @click.option("--port", default="8080")
        def cli(port):
            pass
        param = cli.params[0]
        arg = _extract_arg(param, type_overrides={"port": "integer"})
        assert arg.type == "integer"
        assert arg.default == 8080


# --- _walk_commands ---


class TestWalkCommands:
    def test_single_command_produces_root(self):
        @click.command("mytool")
        @click.argument("input")
        @click.option("--verbose", is_flag=True, help="Verbose")
        def cli(input, verbose):
            pass
        commands = _walk_commands(cli)
        assert len(commands) == 1
        assert commands[0].name == "_root"
        assert commands[0].args is not None
        assert len(commands[0].args) == 2

    def test_group_produces_named_commands(self):
        @click.group("tool")
        def cli():
            pass

        @cli.command()
        def convert():
            """Convert files"""

        @cli.command()
        def validate():
            """Validate files"""

        commands = _walk_commands(cli)
        assert len(commands) == 2
        names = [c.name for c in commands]
        assert "convert" in names
        assert "validate" in names

    def test_nested_groups_space_separated(self):
        @click.group("tool")
        def cli():
            pass

        @cli.group()
        def auth():
            """Auth commands"""

        @auth.command()
        def login():
            """Log in"""

        @auth.command()
        def logout():
            """Log out"""

        commands = _walk_commands(cli)
        assert len(commands) == 2
        names = [c.name for c in commands]
        assert "auth login" in names
        assert "auth logout" in names

    def test_hidden_commands_excluded(self):
        @click.group("tool")
        def cli():
            pass

        @cli.command()
        def public():
            """Public cmd"""

        @cli.command(hidden=True)
        def internal():
            """Hidden cmd"""

        commands = _walk_commands(cli)
        assert len(commands) == 1
        assert commands[0].name == "public"

    def test_annotations_merged(self):
        @click.group("tool")
        def cli():
            pass

        @cli.command()
        @click.argument("input")
        def convert(input):
            """Convert files"""

        from mtp_sdk.types import IODescriptor, Example

        annotations = {
            "convert": CommandAnnotation(
                stdin=IODescriptor(content_type="text/plain", description="Raw input"),
                stdout=IODescriptor(content_type="application/json"),
                examples=[Example(description="Example", command="tool convert data.csv")],
            ),
        }

        commands = _walk_commands(cli, annotations)
        assert len(commands) == 1
        assert commands[0].stdin is not None
        assert commands[0].stdin.content_type == "text/plain"
        assert commands[0].stdout is not None
        assert commands[0].stdout.content_type == "application/json"
        assert commands[0].examples is not None
        assert len(commands[0].examples) == 1

    def test_deeply_nested(self):
        @click.group("tool")
        def cli():
            pass

        @cli.group()
        def a():
            """A"""

        @a.group()
        def b():
            """B"""

        @b.command()
        @click.option("--flag", is_flag=True, help="A flag")
        def c(flag):
            """C"""

        commands = _walk_commands(cli)
        assert len(commands) == 1
        assert commands[0].name == "a b c"

    def test_filtered_params_excluded(self):
        @click.command("tool")
        @click.version_option("1.0.0")
        @click.option("--format", help="Output format")
        def cli(format):
            pass
        commands = _walk_commands(cli)
        assert len(commands) == 1
        arg_names = [a.name for a in commands[0].args]
        assert "--format" in arg_names
        assert "--help" not in arg_names
        assert "--version" not in arg_names


# --- generate_schema ---


class TestGenerateSchema:
    def test_full_schema(self):
        @click.group("filetool")
        def cli():
            """File tool"""

        @cli.command()
        @click.argument("input")
        @click.option("--format", default="json", help="Output format")
        @click.option("--pretty", is_flag=True, help="Pretty print")
        def convert(input, format, pretty):
            """Convert files"""

        @cli.command()
        @click.argument("input")
        @click.option("--strict", is_flag=True, help="Strict mode")
        def validate(input, strict):
            """Validate files"""

        from mtp_sdk.types import IODescriptor, Example

        options = DescribeOptions(
            version="1.0.0",
            commands={
                "convert": CommandAnnotation(
                    arg_descriptions={"input": "Input file"},
                    stdout=IODescriptor(content_type="application/json"),
                    examples=[
                        Example(
                            description="Convert CSV",
                            command="filetool convert data.csv --format json",
                        ),
                    ],
                ),
            },
        )

        schema = generate_schema(cli, options)
        assert schema.name == "filetool"
        assert schema.version == "1.0.0"
        assert schema.spec_version == MTP_SPEC_VERSION
        assert schema.description == "File tool"
        assert len(schema.commands) == 2

        convert_cmd = next(c for c in schema.commands if c.name == "convert")
        assert convert_cmd.args is not None
        input_arg = next(a for a in convert_cmd.args if a.name == "input")
        assert input_arg is not None
        format_arg = next(a for a in convert_cmd.args if a.name == "--format")
        assert format_arg is not None
        pretty_arg = next(a for a in convert_cmd.args if a.name == "--pretty")
        assert pretty_arg is not None
        assert convert_cmd.stdout is not None
        assert convert_cmd.stdout.content_type == "application/json"
        assert convert_cmd.examples is not None
        assert len(convert_cmd.examples) == 1

        validate_cmd = next(c for c in schema.commands if c.name == "validate")
        input_arg = next(a for a in validate_cmd.args if a.name == "input")
        assert input_arg is not None
        strict_arg = next(a for a in validate_cmd.args if a.name == "--strict")
        assert strict_arg is not None

    def test_auth_config(self):
        @click.group("tool")
        def cli():
            """Tool"""

        @cli.command()
        def run():
            """Run it"""

        options = DescribeOptions(
            version="1.0.0",
            auth=AuthConfig(
                type="oauth2",
                description="OAuth2 authentication",
                extra={"authorizationUrl": "https://example.com/auth"},
            ),
        )

        schema = generate_schema(cli, options)
        assert schema.spec_version == MTP_SPEC_VERSION
        assert schema.auth is not None
        assert schema.auth.type == "oauth2"
        assert schema.auth.description == "OAuth2 authentication"

    def test_no_version_produces_empty_string(self):
        @click.group("tool")
        def cli():
            """Tool"""

        @cli.command()
        def run():
            """Run"""

        schema = generate_schema(cli)
        assert schema.version == ""
        assert schema.spec_version == MTP_SPEC_VERSION
