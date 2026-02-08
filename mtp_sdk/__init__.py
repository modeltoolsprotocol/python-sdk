import json
import sys
from typing import Optional

import click

from .introspect import generate_schema
from .types import (
    ArgDescriptor,
    AuthConfig,
    CommandAnnotation,
    CommandDescriptor,
    DescribeOptions,
    Example,
    IODescriptor,
    ToolSchema,
    to_dict,
)

__all__ = [
    "describe",
    "with_describe",
    "ArgDescriptor",
    "AuthConfig",
    "CommandAnnotation",
    "CommandDescriptor",
    "DescribeOptions",
    "Example",
    "IODescriptor",
    "ToolSchema",
    "to_dict",
]


def describe(
    cli: click.BaseCommand,
    options: Optional[DescribeOptions] = None,
) -> ToolSchema:
    """Pure function. Returns ToolSchema without side effects."""
    return generate_schema(cli, options)


def with_describe(
    cli: click.BaseCommand,
    options: Optional[DescribeOptions] = None,
) -> click.BaseCommand:
    """Adds --describe as an eager option. On --describe: print JSON, exit 0."""

    def _describe_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
        if not value:
            return
        schema = describe(cli, options)
        click.echo(json.dumps(to_dict(schema), separators=(",", ":")))
        ctx.exit(0)

    if isinstance(cli, click.Command):
        cli.params.insert(
            0,
            click.Option(
                ["--mtp-describe"],
                is_flag=True,
                is_eager=True,
                expose_value=False,
                help="Output machine-readable MTP JSON schema",
                callback=_describe_callback,
            ),
        )

    return cli
