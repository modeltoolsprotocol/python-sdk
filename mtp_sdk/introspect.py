from typing import Dict, List, Optional

import click
import click.types as ctypes

from .types import (
    ArgDescriptor,
    CommandAnnotation,
    CommandDescriptor,
    DescribeOptions,
    ToolSchema,
)

MTP_SPEC_VERSION = "2026-02-07"


def _is_sentinel(value: object) -> bool:
    return type(value).__name__ == "Sentinel"


def _infer_type(
    param: click.Parameter,
    type_overrides: Optional[Dict[str, str]] = None,
) -> tuple:
    """Return (mtp_type, values) for a Click parameter."""
    name = param.name or ""
    if type_overrides and name in type_overrides:
        return type_overrides[name], None

    pt = param.type

    if isinstance(param, click.Option) and param.is_flag:
        return "boolean", None

    if isinstance(pt, click.Choice):
        return "enum", list(pt.choices)

    if param.nargs == -1 or (isinstance(param, click.Option) and param.multiple):
        return "array", None

    if isinstance(pt, (ctypes.IntParamType, click.IntRange)):
        return "integer", None
    if isinstance(pt, (ctypes.FloatParamType, click.FloatRange)):
        return "number", None
    if isinstance(pt, ctypes.BoolParamType):
        return "boolean", None
    if isinstance(pt, click.Path):
        return "path", None

    # Count options (e.g. -vvv)
    if isinstance(param, click.Option) and param.count:
        return "integer", None

    return "string", None


_FILTERED_NAMES = frozenset(("help", "version", "mtp_describe"))


def _is_filtered_param(param: click.Parameter) -> bool:
    if getattr(param, "hidden", False):
        return True
    name = param.name or ""
    if name in _FILTERED_NAMES:
        return True
    return False


def _option_display_name(param: click.Option) -> str:
    """Return the longest option string (prefer --long over -s)."""
    opts = param.opts + param.secondary_opts
    return max(opts, key=len) if opts else param.name or ""


def _extract_arg(
    param: click.Parameter,
    type_overrides: Optional[Dict[str, str]] = None,
    arg_descriptions: Optional[Dict[str, str]] = None,
) -> ArgDescriptor:
    mtp_type, values = _infer_type(param, type_overrides)

    if isinstance(param, click.Option):
        name = _option_display_name(param)
    else:
        name = param.name or ""

    desc = None
    if isinstance(param, click.Option):
        desc = param.help
    elif arg_descriptions and param.name and param.name in arg_descriptions:
        desc = arg_descriptions[param.name]

    arg = ArgDescriptor(name=name, type=mtp_type)
    if desc:
        arg.description = desc
    if values:
        arg.values = values

    if isinstance(param, click.Option):
        arg.required = param.required
    elif isinstance(param, click.Argument):
        arg.required = param.required

    default = param.default
    # Skip None, empty tuples, sentinels, and False for boolean flags
    if (
        default is not None
        and default != ()
        and not _is_sentinel(default)
        and not (isinstance(param, click.Option) and param.is_flag and default is False)
    ):
        if (
            mtp_type in ("integer", "number")
            and isinstance(default, str)
        ):
            try:
                default = int(default) if mtp_type == "integer" else float(default)
            except (ValueError, TypeError):
                pass
        arg.default = default

    return arg


def _walk_commands(
    cmd: click.BaseCommand,
    annotations: Optional[Dict[str, CommandAnnotation]] = None,
    parent_path: Optional[str] = None,
) -> List[CommandDescriptor]:
    if isinstance(cmd, click.Group):
        sub_names = cmd.list_commands(click.Context(cmd, info_name=""))
        visible = []
        for sn in sub_names:
            sub = cmd.get_command(click.Context(cmd, info_name=""), sn)
            if sub and not getattr(sub, "hidden", False):
                visible.append((sn, sub))

        if visible:
            results = []
            for sn, sub in visible:
                sub_path = f"{parent_path} {sn}" if parent_path else sn
                results.extend(_walk_commands(sub, annotations, sub_path))
            return results

    # Leaf command or no visible subcommands
    name = parent_path or "_root"
    return [_build_command(cmd, name, annotations.get(name) if annotations else None)]


def _build_command(
    cmd: click.BaseCommand,
    name: str,
    annotation: Optional[CommandAnnotation] = None,
) -> CommandDescriptor:
    help_text = ""
    if isinstance(cmd, click.Command):
        help_text = cmd.help or ""
    # Click wraps help text with newlines sometimes; take the short description
    if help_text:
        help_text = help_text.strip().split("\n")[0].strip()

    descriptor = CommandDescriptor(name=name, description=help_text)

    type_overrides = annotation.arg_types if annotation else None
    arg_descriptions = annotation.arg_descriptions if annotation else None

    args: List[ArgDescriptor] = []
    if isinstance(cmd, click.Command):
        for param in cmd.params:
            if _is_filtered_param(param):
                continue
            args.append(_extract_arg(param, type_overrides, arg_descriptions))

    if args:
        # Positional arguments first, then options
        positional = [a for a in args if not a.name.startswith("-")]
        options = [a for a in args if a.name.startswith("-")]
        descriptor.args = positional + options

    if annotation:
        if annotation.stdin:
            descriptor.stdin = annotation.stdin
        if annotation.stdout:
            descriptor.stdout = annotation.stdout
        if annotation.examples:
            descriptor.examples = annotation.examples

    return descriptor


def generate_schema(
    cli: click.BaseCommand,
    options: Optional[DescribeOptions] = None,
) -> ToolSchema:
    name = ""
    if isinstance(cli, click.Command):
        name = cli.name or ""

    version = ""
    if options and options.version:
        version = options.version

    description = ""
    if isinstance(cli, click.Command):
        description = cli.help or ""
    if description:
        description = description.strip().split("\n")[0].strip()

    commands = _walk_commands(
        cli,
        options.commands if options else None,
    )

    schema = ToolSchema(
        name=name,
        version=version,
        description=description,
        spec_version=MTP_SPEC_VERSION,
        commands=commands,
    )

    if options and options.auth:
        schema.auth = options.auth

    return schema
