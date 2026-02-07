from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional


@dataclass
class Example:
    description: str
    command: str
    output: Optional[str] = None


@dataclass
class IODescriptor:
    content_type: Optional[str] = None
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


@dataclass
class ArgDescriptor:
    name: str
    type: str
    description: Optional[str] = None
    required: Optional[bool] = None
    default: Optional[Any] = None
    values: Optional[List[str]] = None


@dataclass
class CommandDescriptor:
    name: str
    description: str
    args: Optional[List[ArgDescriptor]] = None
    stdin: Optional[IODescriptor] = None
    stdout: Optional[IODescriptor] = None
    examples: Optional[List[Example]] = None


@dataclass
class AuthConfig:
    type: str
    description: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class ToolSchema:
    name: str
    version: str
    description: str
    spec_version: str = ""
    commands: List[CommandDescriptor] = field(default_factory=list)
    auth: Optional[AuthConfig] = None


@dataclass
class CommandAnnotation:
    stdin: Optional[IODescriptor] = None
    stdout: Optional[IODescriptor] = None
    examples: Optional[List[Example]] = None
    arg_types: Optional[Dict[str, str]] = None
    arg_descriptions: Optional[Dict[str, str]] = None


@dataclass
class DescribeOptions:
    version: Optional[str] = None
    commands: Optional[Dict[str, CommandAnnotation]] = None
    auth: Optional[AuthConfig] = None


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def to_dict(obj: Any) -> Any:
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if not hasattr(obj, "__dataclass_fields__"):
        return obj
    result = {}
    for f in fields(obj):
        val = getattr(obj, f.name)
        if val is None:
            continue
        key = _snake_to_camel(f.name)
        if isinstance(val, list):
            result[key] = [to_dict(item) for item in val]
        elif hasattr(val, "__dataclass_fields__"):
            result[key] = to_dict(val)
        elif isinstance(val, dict):
            result[key] = val
        else:
            result[key] = val
    # Flatten AuthConfig.extra into the parent dict
    if isinstance(obj, AuthConfig) and obj.extra:
        del result["extra"]
        for k, v in obj.extra.items():
            result[k] = v
    return result
