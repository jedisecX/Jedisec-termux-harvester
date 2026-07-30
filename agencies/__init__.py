import pkgutil
import importlib

_REGISTRY = {}


def _discover():
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{module_name}")
        state = getattr(module, "STATE", None)
        if state is not None:
            _REGISTRY[state.state_code] = state


_discover()


def available_states():
    return list(_REGISTRY.keys())


def get_state(code):
    return _REGISTRY[code]


def all_states():
    return dict(_REGISTRY)
