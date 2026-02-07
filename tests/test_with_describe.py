import json

import click
from click.testing import CliRunner

from mtp_sdk import describe, with_describe
from mtp_sdk.types import (
    AuthConfig,
    CommandAnnotation,
    DescribeOptions,
    Example,
    IODescriptor,
)


class TestDescribe:
    def test_multi_command_schema(self):
        @click.group("filetool")
        def cli():
            """Convert and validate files"""

        @cli.command()
        @click.argument("input")
        @click.option("--format", default="json", help="Output format")
        @click.option("--pretty", is_flag=True, help="Pretty-print output")
        def convert(input, format, pretty):
            """Convert a file"""

        @cli.command()
        @click.argument("input")
        def validate(input):
            """Validate a file"""

        options = DescribeOptions(
            version="2.0.0",
            commands={
                "convert": CommandAnnotation(
                    arg_descriptions={"input": "Input file path"},
                    stdin=IODescriptor(content_type="text/plain", description="Raw input"),
                    stdout=IODescriptor(content_type="application/json"),
                    examples=[
                        Example(
                            description="Convert CSV to JSON",
                            command="filetool convert data.csv --format json",
                        ),
                    ],
                ),
            },
        )

        schema = describe(cli, options)
        assert schema.name == "filetool"
        assert schema.version == "2.0.0"
        assert schema.spec_version == "2026-02-07"
        assert len(schema.commands) == 2

        convert_cmd = schema.commands[0]
        assert convert_cmd.name == "convert"
        assert convert_cmd.stdin is not None
        assert convert_cmd.stdin.content_type == "text/plain"
        assert convert_cmd.stdout is not None
        assert convert_cmd.stdout.content_type == "application/json"
        assert convert_cmd.examples is not None
        assert len(convert_cmd.examples) == 1

        format_arg = next(a for a in convert_cmd.args if a.name == "--format")
        assert format_arg.default == "json"
        assert format_arg.type == "string"

        pretty_arg = next(a for a in convert_cmd.args if a.name == "--pretty")
        assert pretty_arg.type == "boolean"

    def test_single_command_produces_root(self):
        @click.command("greet")
        @click.argument("name")
        @click.option("--loud", is_flag=True, help="Shout the greeting")
        def cli(name, loud):
            """Greet someone"""

        options = DescribeOptions(
            version="1.0.0",
            commands={
                "_root": CommandAnnotation(
                    arg_descriptions={"name": "Name to greet"},
                ),
            },
        )

        schema = describe(cli, options)
        assert len(schema.commands) == 1
        assert schema.commands[0].name == "_root"
        assert len(schema.commands[0].args) == 2

    def test_auth_config(self):
        @click.group("tool")
        def cli():
            """A tool"""

        @cli.command()
        def run():
            """Run"""

        options = DescribeOptions(
            version="1.0.0",
            auth=AuthConfig(
                type="api-key",
                description="API key auth",
                extra={"envVar": "TOOL_API_KEY"},
            ),
        )

        schema = describe(cli, options)
        assert schema.auth is not None
        assert schema.auth.type == "api-key"
        assert schema.auth.description == "API key auth"


class TestWithDescribe:
    def test_adds_describe_option(self):
        @click.command("tool")
        def cli():
            """A tool"""

        with_describe(cli, DescribeOptions(version="1.0.0"))
        param_names = [p.name for p in cli.params]
        assert "mtp_describe" in param_names

    def test_returns_cli_for_chaining(self):
        @click.command("tool")
        def cli():
            """A tool"""

        result = with_describe(cli)
        assert result is cli

    def test_describe_outputs_json_and_exits_zero(self):
        @click.group("filetool")
        def cli():
            """File tool"""

        @cli.command()
        @click.argument("input")
        @click.option("--format", default="json", help="Format")
        def convert(input, format):
            """Convert files"""

        with_describe(cli, DescribeOptions(
            version="1.0.0",
            commands={
                "convert": CommandAnnotation(
                    arg_descriptions={"input": "Input"},
                    stdout=IODescriptor(content_type="application/json"),
                ),
            },
        ))

        runner = CliRunner()
        result = runner.invoke(cli, ["--mtp-describe"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert schema["name"] == "filetool"
        assert schema["version"] == "1.0.0"
        assert schema["specVersion"] == "2026-02-07"
        assert len(schema["commands"]) == 1
        assert schema["commands"][0]["name"] == "convert"
        assert schema["commands"][0]["stdout"] == {"contentType": "application/json"}

    def test_describe_excluded_from_schema(self):
        @click.command("tool")
        @click.option("--format", help="Format")
        def cli(format):
            """A tool"""

        with_describe(cli, DescribeOptions(version="1.0.0"))
        schema = describe(cli, DescribeOptions(version="1.0.0"))

        assert len(schema.commands) == 1
        assert schema.commands[0].name == "_root"
        arg_names = [a.name for a in schema.commands[0].args]
        assert "--format" in arg_names
        assert "--mtp-describe" not in arg_names

    def test_normal_operation_still_works(self):
        @click.command("greet")
        @click.argument("name")
        def cli(name):
            """Greet someone"""
            click.echo(f"Hello, {name}!")

        with_describe(cli, DescribeOptions(version="1.0.0"))

        runner = CliRunner()
        result = runner.invoke(cli, ["World"])
        assert result.exit_code == 0
        assert "Hello, World!" in result.output


class TestToDictSerialization:
    def test_camel_case_keys(self):
        """Verify JSON output uses camelCase keys."""
        @click.group("tool")
        def cli():
            """A tool"""

        @cli.command()
        @click.argument("input")
        def convert(input):
            """Convert"""

        with_describe(cli, DescribeOptions(
            version="1.0.0",
            commands={
                "convert": CommandAnnotation(
                    arg_descriptions={"input": "Input file"},
                    stdin=IODescriptor(content_type="text/plain"),
                ),
            },
        ))

        runner = CliRunner()
        result = runner.invoke(cli, ["--mtp-describe"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        # contentType, not content_type
        assert "contentType" in schema["commands"][0]["stdin"]

    def test_none_fields_omitted(self):
        """Verify None fields are not in JSON output."""
        @click.command("tool")
        def cli():
            """A tool"""

        with_describe(cli, DescribeOptions(version="1.0.0"))

        runner = CliRunner()
        result = runner.invoke(cli, ["--mtp-describe"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert schema["specVersion"] == "2026-02-07"
        assert "auth" not in schema
        assert "stdin" not in schema["commands"][0]

    def test_auth_extra_flattened(self):
        """Verify AuthConfig extra fields are flattened into the auth dict."""
        @click.group("tool")
        def cli():
            """A tool"""

        @cli.command()
        def run():
            """Run"""

        with_describe(cli, DescribeOptions(
            version="1.0.0",
            auth=AuthConfig(
                type="oauth2",
                description="OAuth2",
                extra={"authorizationUrl": "https://example.com/auth"},
            ),
        ))

        runner = CliRunner()
        result = runner.invoke(cli, ["--mtp-describe"])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert schema["auth"]["type"] == "oauth2"
        assert schema["auth"]["authorizationUrl"] == "https://example.com/auth"
        assert "extra" not in schema["auth"]
