import pkgutil
import importlib
import inspect
from .base import SearchEngine

_REGISTRY = {}


def _discover():
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{module_name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, SearchEngine) and obj is not SearchEngine:
                instance = obj()
                _REGISTRY[instance.name] = instance


_discover()


def available_engines():
    return list(_REGISTRY.keys())


def get_engine(name):
    return _REGISTRY[name]


def all_engines():
    return dict(_REGISTRY)
