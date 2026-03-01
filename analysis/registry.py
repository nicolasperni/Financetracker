from dataclasses import dataclass
from typing import Callable
import importlib
import pkgutil


@dataclass
class AnalysisEntry:
    name: str
    func: Callable
    description: str = ""
    order: int = 100


_registry: dict[str, AnalysisEntry] = {}


def register(name: str, description: str = "", order: int = 100):
    """Decorator to register an analysis function.

    Usage:
        @register("Portfolio Allocation", order=10)
        def render():
            ...
    """

    def decorator(func: Callable):
        _registry[name] = AnalysisEntry(
            name=name,
            func=func,
            description=description,
            order=order,
        )
        return func

    return decorator


def get_all_analyses() -> list[AnalysisEntry]:
    """Return all registered analyses sorted by order."""
    return sorted(_registry.values(), key=lambda a: a.order)


def auto_discover():
    """Import all modules in the analysis package to trigger registration."""
    if _registry:
        return  # Already discovered
    import analysis

    for _importer, modname, _ispkg in pkgutil.iter_modules(analysis.__path__):
        if modname != "registry":
            importlib.import_module(f"analysis.{modname}")
