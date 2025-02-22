import inspect
from dataclasses import dataclass, field
from typing import Any

import pytest

from kayaku import backend as json5
from kayaku.doc_parse import store_field_description
from kayaku.format import format_with_model
from kayaku.pretty import Prettifier, Quote


def test_format_model():
    @dataclass
    class D:
        a: int = 5

    @dataclass
    class Model:
        c: list[str]
        "Fantasy C"
        e: Any
        "Any E"
        a: int = 4
        """Annotation: A"""
        b: dict[str, str] = field(default_factory=lambda: {"a": "c"})
        """B
        Annotation: B
        """
        default: D = field(default_factory=D)

    store_field_description(Model, Model.__dataclass_fields__)

    data = json5.loads(
        """
{
    /*
     * Annotation: A
     *
     * @type: int
     */
    a: 3,
    d: 5,
    c: ["123"]
    /*
     * B
     * Annotation: B
     *
     * @type: dict[str, str]
     */
}
"""
    )

    format_with_model(data, Model)

    assert json5.dumps(
        Prettifier(key_quote=Quote.DOUBLE).prettify(data)
    ) == inspect.cleandoc(
        """\
        {
            /*
             * Annotation: A
             *
             * @type: int
             */
            "a": 3,
            "d": 5,
            /*
             * Fantasy C
             *
             * @type: list[str]
             */
            "c": ["123"],
            /*
             * Any E
             *
             * @type: Any
             */
            "e": null,
            /*
             * B
             * Annotation: B
             *
             * @type: dict[str, str]
             */
            "b": {"a": "c"},
            /*@type: format.test_format_model.<locals>.D*/
            "default": {"a": 5}
        }
        """
    )

    with pytest.raises(TypeError):
        format_with_model({}, Model)
