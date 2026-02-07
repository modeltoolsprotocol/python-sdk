# mtp-sdk

Add MTP `--mtp-describe` support to any Click CLI. One function call, zero boilerplate.

## Install

```bash
pip install mtp-sdk click
```

## Quick Start

```python
import click
from mtp_sdk import with_describe, DescribeOptions, CommandAnnotation, Example, IODescriptor

@click.group()
def cli():
    """Convert and validate files"""

@cli.command()
@click.argument("input")
@click.option("--format", default="json", help="Output format")
@click.option("--pretty", is_flag=True, help="Pretty-print output")
def convert(input, format, pretty):
    """Convert a file"""

with_describe(cli, DescribeOptions(
    version="1.0.0",
    commands={
        "convert": CommandAnnotation(
            arg_descriptions={"input": "Input file path"},
            stdin=IODescriptor(content_type="text/plain", description="Raw input"),
            stdout=IODescriptor(content_type="application/json"),
            examples=[
                Example(description="Convert CSV", command="filetool convert data.csv --format json"),
            ],
        ),
    },
))

if __name__ == "__main__":
    cli()
```

```bash
$ filetool --mtp-describe          # MTP JSON schema
$ filetool convert data.csv    # normal operation
```

## API

### `with_describe(cli, options?)`

Adds `--mtp-describe` to an existing Click command or group. When invoked, outputs MTP-compliant JSON and exits.

- **cli** - a Click `BaseCommand` instance (your root command or group)
- **options.version** - version string for the tool
- **options.commands** - per-command annotations keyed by command name (stdin, stdout, examples, arg_types, arg_descriptions)
- **options.auth** - authentication config to include in the schema
- Returns the cli for chaining

### `describe(cli, options?)`

Pure function. Returns the `ToolSchema` object without side effects. Useful for testing or programmatic access.

## How It Works

The SDK introspects Click's own data structures (params, type objects, subcommands) so you never duplicate information. Supplemental metadata (stdin/stdout/examples) that Click doesn't model is provided via the options map.

### Type Inference

Arg types describe flags and positional arguments, which are always scalar on the command line:

| Click signal | MTP type |
|---|---|
| `Option.is_flag` | `"boolean"` |
| `click.Choice(...)` | `"enum"` + `values` |
| `Option.multiple` / `nargs=-1` | `"array"` |
| `click.INT` / `IntRange` | `"integer"` |
| `click.FLOAT` / `FloatRange` | `"number"` |
| `click.BOOL` | `"boolean"` |
| `click.Path(...)` | `"path"` |
| `Option.count` | `"integer"` |
| explicit `arg_types` override | whatever you say |
| everything else | `"string"` |

For structured data flowing through stdin/stdout, use the `schema` field in IO descriptors. This supports full JSON Schema (draft 2020-12): nested objects, arrays, unions, pattern validation, conditional fields.

### Structured IO

When a command accepts or produces JSON, describe the shape with a JSON Schema:

```python
with_describe(cli, DescribeOptions(
    version="1.0.0",
    commands={
        "process": CommandAnnotation(
            stdin=IODescriptor(
                content_type="application/json",
                description="Configuration to process",
                schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "settings": {
                            "type": "object",
                            "properties": {
                                "retries": {"type": "integer"},
                                "endpoints": {
                                    "type": "array",
                                    "items": {"type": "string", "format": "uri"},
                                },
                            },
                        },
                    },
                    "required": ["name"],
                },
            ),
            stdout=IODescriptor(
                content_type="application/json",
                schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["ok", "error"]},
                        "results": {"type": "array", "items": {"type": "object"}},
                    },
                },
            ),
        ),
    },
))

### Command Naming

- Groups with subcommands: each leaf command gets a space-separated path (e.g., `"auth login"`)
- Commands with no subcommands: single command named `"_root"`
- Hidden commands and options are excluded

### Argument Descriptions

Click arguments don't support `help` text natively. Use `arg_descriptions` in your annotation:

```python
CommandAnnotation(
    arg_descriptions={"input_file": "Input file path"},
)
```

### Filtered Options

These are automatically excluded from schema output: `--help`, `--version`, `--mtp-describe`, and any hidden options.

## Single-Command Tools

Tools with no subcommands work the same way:

```python
import click
from mtp_sdk import with_describe, DescribeOptions

@click.command()
@click.argument("name")
@click.option("--loud", is_flag=True, help="Shout the greeting")
def greet(name, loud):
    """Greet someone"""
    msg = f"Hello, {name}!"
    click.echo(msg.upper() if loud else msg)

with_describe(greet, DescribeOptions(version="1.0.0"))

if __name__ == "__main__":
    greet()
```

This produces a schema with a single `_root` command.
