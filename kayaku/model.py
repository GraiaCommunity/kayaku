import inspect
from typing import Tuple, Type, TypeVar, Union, cast

from loguru import logger
from pydantic import BaseConfig, BaseModel, Extra

from .doc_parse import store_field_description
from .pretty import Prettifier
from .utils import update


class ConfigModel(BaseModel):
    def __init_subclass__(cls, domain: str) -> None:
        domain_tup: Tuple[str, ...] = tuple(domain.split("."))
        if not all(domain_tup):
            raise ValueError(f"{domain!r} contains empty segment!")
        from .domain import _reg, domain_map

        if domain_tup in domain_map:
            raise NameError(
                f"{domain!r} is already occupied by {domain_map[domain_tup]!r}"
            )
        domain_map[domain_tup] = cls
        if _reg.initialized:
            raise RuntimeError(
                f"kayaku is already fully initialized, adding {cls} is not allowed."
            )
        else:
            _reg.postponed.append(domain_tup)
        store_field_description(cls)
        return super().__init_subclass__()

    class Config(BaseConfig):
        extra = Extra.ignore
        validate_assignment: bool = True


T_Model = TypeVar("T_Model", bound=ConfigModel)


def create(cls: Type[T_Model], flush: bool = False) -> T_Model:
    from .domain import _reg

    if flush:
        from . import backend as json5

        fmt_path = _reg.model_path[cls]
        document = json5.loads(fmt_path.path.read_text("utf-8"))
        container = document
        for sect in fmt_path.section:
            container = container[sect]
        _reg.model_map[cls] = cls.parse_obj(container)

    return cast(T_Model, _reg.model_map[cls])


def save(model: Union[T_Model, Type[T_Model]]) -> None:
    from . import backend as json5
    from .domain import _reg

    inst: ConfigModel = _reg.model_map[model] if isinstance(model, type) else model
    fmt_path = _reg.model_path[inst.__class__]
    document = json5.loads(fmt_path.path.read_text("utf-8"))
    container = document
    for sect in fmt_path.section:
        container = container.setdefault(sect, {})
    update(container, inst.dict(by_alias=True))
    fmt_path.path.write_text(json5.dumps(Prettifier().prettify(document)), "utf-8")
