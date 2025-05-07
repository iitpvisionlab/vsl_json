from __future__ import annotations
import json
from typing import Any
from os import PathLike

__version__ = "0.0.3"

StrOrBytesPath = str | bytes | PathLike[str] | PathLike[bytes]


class VSLJSONEncoder(json.JSONEncoder):
    """A JSON Encoder that puts small containers on single lines."""

    CONTAINER_TYPES = (list, tuple, dict)
    """Container datatypes include primitives or other containers."""

    MAX_WIDTH = 79
    """Maximum width of a container that might be put on a single line."""

    MAX_ITEMS = 10
    """Maximum number of items in container that might be put on single line."""

    def __init__(self, *args, **kwargs) -> None:
        # using this class without indentation is pointless
        if kwargs.get("indent") is None:
            kwargs["indent"] = "  "
        super().__init__(*args, **kwargs)
        self.indentation_level = 0

    def encode(self, o: Any) -> str:
        """Encode JSON object *o* with respect to single line lists."""
        if isinstance(o, float):
            if o.is_integer():
                return f"{o}"  # don't need extra zeroes
            return f"{o:0.6f}".rstrip("0").rstrip(
                "."
            )  # 1e-6 of a pixel should be all right
        if isinstance(o, (list, tuple)):
            return self._encode_list(o)
        if isinstance(o, dict):
            return self._encode_object(o)
        return json.dumps(
            o,
            skipkeys=self.skipkeys,
            ensure_ascii=self.ensure_ascii,
            check_circular=self.check_circular,
            allow_nan=self.allow_nan,
            sort_keys=self.sort_keys,
            indent=self.indent,
            separators=(self.item_separator, self.key_separator),
            default=self.default if hasattr(self, "default") else None,
        )

    def _encode_list(self, o: list[Any]) -> str:
        if self._primitives_only(o) and len(o) <= self.MAX_ITEMS:
            data = "[" + ", ".join(self.encode(el) for el in o) + "]"
            if len(data) + self.indentation_level * 2 < self.MAX_WIDTH:
                return data
        self.indentation_level += 1
        output = [self.indent_str + self.encode(el) for el in o]
        self.indentation_level -= 1
        return "[\n" + ",\n".join(output) + "\n" + self.indent_str + "]"

    def _encode_object(self, o: dict[Any, Any]):
        if not o:
            return "{}"

        # ensure keys are converted to strings
        o = {str(k) if k is not None else "null": v for k, v in o.items()}

        if self.sort_keys:
            o = dict(sorted(o.items(), key=lambda x: x[0]))

        self.indentation_level += 1
        output = [
            f"{self.indent_str}{json.dumps(k, ensure_ascii=self.ensure_ascii)}: {self.encode(v)}"
            for k, v in o.items()
        ]
        self.indentation_level -= 1

        return "{\n" + ",\n".join(output) + "\n" + self.indent_str + "}"

    def iterencode(self, o: Any, **kwargs) -> str:
        """Required to also work with `json.dump`."""
        return self.encode(o)

    def _primitives_only(
        self, o: list[Any] | tuple[Any] | dict[Any, Any]
    ) -> bool:
        if isinstance(o, (list, tuple)):
            return not any(isinstance(el, self.CONTAINER_TYPES) for el in o)
        assert isinstance(o, dict)
        return not any(
            isinstance(el, self.CONTAINER_TYPES) for el in o.values()
        )

    @property
    def indent_str(self) -> str:
        assert isinstance(self.indent, str)
        return self.indentation_level * self.indent


def load(json_filename: StrOrBytesPath) -> Any:
    with open(json_filename, "r", encoding="utf-8") as inp:
        return json.load(inp)


def dump(json_filename: StrOrBytesPath, data: Any) -> None:
    # save first to raw_json, as `json.dump` will corrupt file in extreme cases
    raw_json = json.dumps(
        data,
        allow_nan=False,
        sort_keys=True,
        ensure_ascii=False,
        cls=VSLJSONEncoder,
    )

    with open(json_filename, "w", encoding="utf-8") as out:
        out.write(raw_json)
