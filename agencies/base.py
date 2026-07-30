from dataclasses import dataclass


@dataclass
class Agency:
    code: str
    name: str
    query: str


@dataclass
class StateModule:
    state_code: str
    state_name: str
    agencies: dict  # code -> Agency


def build_state(state_code, state_name, raw):
    """raw: dict of code -> (name, query), the same shape the original
    single-state script used. Porting an existing agency list into a
    plugin module is just: copy the dict in, call this once."""
    agencies = {code: Agency(code, name, query) for code, (name, query) in raw.items()}
    return StateModule(state_code=state_code, state_name=state_name, agencies=agencies)
