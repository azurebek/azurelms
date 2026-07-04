from typing import Type, Dict, Any

FORM_REGISTRY: Dict[str, Type[Any]] = {}

def register_form(name: str):
    """
    Decorator to register a BaseSmartForm class into the global registry.
    """
    def decorator(cls):
        FORM_REGISTRY[name] = cls
        return cls
    return decorator

def get_form_class(name: str) -> Type[Any]:
    if name not in FORM_REGISTRY:
        raise ValueError(f"Form '{name}' not found in registry.")
    return FORM_REGISTRY[name]
