#!/usr/bin/env python3

import click

from mtp_sdk import with_describe, CommandAnnotation, DescribeOptions, Example, IODescriptor


@click.group("filetool")
def cli():
    """Convert and validate files between formats"""


@cli.command()
@click.argument("input")
@click.option("--format", "fmt", default="json", help="Output format")
@click.option("--pretty", is_flag=True, help="Pretty-print output")
def convert(input, fmt, pretty):
    """Convert a file from one format to another"""
    click.echo(f"Converting {input} to {fmt}")
    if pretty:
        click.echo("(pretty-printed)")


@cli.command()
@click.argument("input")
@click.option("--strict", is_flag=True, help="Enable strict validation mode")
def validate(input, strict):
    """Check if a file is well-formed and valid"""
    click.echo(f"Validating {input}{' (strict)' if strict else ''}")


with_describe(cli, DescribeOptions(
    version="1.2.0",
    commands={
        "convert": CommandAnnotation(
            arg_descriptions={"input": "Input file path"},
            stdin=IODescriptor(
                content_type="text/plain",
                description="Raw input data (alternative to file path)",
            ),
            stdout=IODescriptor(
                content_type="application/json",
                description="Converted output",
            ),
            examples=[
                Example(
                    description="Convert a CSV file to JSON",
                    command="filetool convert data.csv --format json --pretty",
                ),
                Example(
                    description="Pipe from stdin",
                    command="cat data.csv | filetool convert - --format yaml",
                ),
            ],
        ),
        "validate": CommandAnnotation(
            arg_descriptions={"input": "File to validate"},
            examples=[
                Example(
                    description="Validate a JSON file",
                    command="filetool validate config.json",
                    output='{"valid": true, "errors": []}',
                ),
            ],
        ),
    },
))


if __name__ == "__main__":
    cli()
