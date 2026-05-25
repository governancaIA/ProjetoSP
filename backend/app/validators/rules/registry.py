"""
Global registry of validation rules with decorator-based registration
"""
from typing import Type
from app.validators.rules.base import BaseRule


_registry: dict[str, Type[BaseRule]] = {}


def register(cls: Type[BaseRule]) -> Type[BaseRule]:
    """
    Decorator to register a rule class in the global registry.

    Usage:
        @register
        class MyRule(BaseRule):
            rule_id = "my_rule"
            rule_version = "1.0.0"
            ...

    Args:
        cls: Rule class to register

    Returns:
        The same class (passthrough decorator)
    """
    if not hasattr(cls, 'rule_id') or cls.rule_id is None:
        raise ValueError(f"Rule class {cls.__name__} must define 'rule_id'")
    if not hasattr(cls, 'rule_version') or cls.rule_version is None:
        raise ValueError(f"Rule class {cls.__name__} must define 'rule_version'")

    _registry[cls.rule_id] = cls
    return cls


def get_active_rules() -> list[BaseRule]:
    """
    Get instances of all registered rules.

    Returns:
        List of BaseRule instances
    """
    return [cls() for cls in _registry.values()]


def get_rule(rule_id: str) -> BaseRule:
    """
    Get a single rule instance by ID.

    Args:
        rule_id: Rule identifier

    Returns:
        BaseRule instance or None if not found

    Raises:
        KeyError if rule not found
    """
    return _registry[rule_id]()


def list_rules() -> list[str]:
    """
    List all registered rule IDs.

    Returns:
        List of rule IDs
    """
    return list(_registry.keys())
