"""Uniformed JSON backend for JSON5.

Ported from <https://github.com/noirbizarre/json4humans> under the MIT license.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, TextIO

from lark.lark import Lark

from .encode import Encoder
from .env import DEBUG
from .transform import transformer

parser = Lark.open(
    "grammar/json5.lark",
    rel_to=__file__,
    lexer="auto",
    parser="lalr",
    start="value",
    maybe_placeholders=False,
    regex=True,
    transformer=transformer,
)

debug_parser = Lark.open(
    "grammar/json5.lark",
    rel_to=__file__,
    lexer="auto",
    parser="lalr",
    start="value",
    maybe_placeholders=False,
    regex=True,
    transformer=None,
)


def loads(src: str) -> Any:
    """
    Parse JSON from a string
    """
    if not DEBUG.get():
        return parser.parse(src)
    tree = debug_parser.parse(src)
    return transformer.transform(tree)


def load(file: TextIO | Path) -> str:
    """
    Parse JSON from a file-like object
    """
    data = file.read_text() if isinstance(file, Path) else file.read()
    return loads(data)


def dumps(obj: Any) -> str:
    """
    Serialize JSON to a string
    """
    fp = io.StringIO()
    Encoder(fp).encode(obj)
    return fp.getvalue()


def dump(obj: Any, out: TextIO | Path):
    """
    Serialize JSON to a file-like object
    """
    out = out.open("w") if isinstance(out, Path) else out
    Encoder(out).encode(obj)
