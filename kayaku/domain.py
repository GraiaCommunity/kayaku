from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, Tuple, Type

import pydantic

from kayaku.backend.types import JObject
from kayaku.utils import gen_schema

from .format import format_with_model
from .model import ConfigModel
from .spec import FormattedPath, parse_path, parse_source
from .storage import insert, lookup

DomainType = Tuple[str, ...]

domain_map: dict[DomainType, type[ConfigModel]] = {}
file_map: dict[Path, dict[DomainType, list[type[ConfigModel]]]] = {}


class _Reg:
    initialized: ClassVar[bool] = False

    postponed: ClassVar[list[DomainType]] = []

    model_path: ClassVar[dict[type[ConfigModel], FormattedPath]] = {}

    model_map: ClassVar[dict[type[ConfigModel], ConfigModel]] = {}

    domain_occupation: ClassVar[dict[Path, set[DomainType]]] = {}


def _insert_domain(domains: DomainType) -> None:
    cls: Type[ConfigModel] = domain_map[domains]
    fmt_path: FormattedPath = lookup(list(domains))
    path = fmt_path.path
    section = tuple(fmt_path.section)
    if section in _Reg.domain_occupation.setdefault(path, set()):
        raise NameError(f"{path.as_posix()}::{'.'.join(section)} is occupied!")
    for f_name in cls.__fields__:
        sub_sect = section + (f_name,)
        if sub_sect in _Reg.domain_occupation[path]:
            raise NameError(f"{path.as_posix()}::{'.'.join(sub_sect)} is occupied!")
        _Reg.domain_occupation[path].add(sub_sect)
    file_map.setdefault(path, {}).setdefault(section, []).append(cls)
    _Reg.model_path[cls] = fmt_path


def _bootstrap():
    for domain in _Reg.postponed:
        _insert_domain(domain)
    _bootstrap_files()
    _Reg.initialized = True


def _bootstrap_files():
    from . import backend as json5
    from .pretty import Prettifier

    for path, sect_map in file_map.items():
        document = json5.loads(path.read_text(encoding="utf-8") or "{}")
        failed: list[pydantic.ValidationError] = []
        model_list: list[tuple[DomainType, type[pydantic.BaseModel]]] = []
        for sect, classes in sect_map.items():
            model_list.extend((sect, cls) for cls in classes)
            container = document
            for s in sect:
                container = container.setdefault(s, JObject())
            for cls in classes:
                try:
                    _Reg.model_map[cls] = cls.parse_obj(container)
                except pydantic.ValidationError as e:
                    failed.append(e)
            for cls in classes:
                # Copy schema's "properties" and "$defs" out
                format_with_model(container, cls)
        schema_path = path.with_suffix(".schema.json")  # TODO: Customization
        document["$schema"] = schema_path.as_uri()
        schema_path.write_text(json5.dumps(gen_schema(model_list)), encoding="utf-8")
        path.write_text(
            json5.dumps(Prettifier().prettify(document, clean=True)), encoding="utf-8"
        )
        if failed:
            raise ValueError(f"{len(failed)} models failed to validate.", failed)


def initialize(specs: Dict[str, str], *, __bootstrap: bool = True) -> None:
    exceptions: list[Exception] = []
    for src, path in specs.items():
        try:
            src_spec = parse_source(src)
            path_spec = parse_path(path)
            insert(src_spec, path_spec)
        except Exception as e:
            exceptions.append(e)
    if exceptions:
        raise ValueError(
            f"{len(exceptions)} occurred during initialization.", exceptions
        )
    if __bootstrap:
        _bootstrap()
