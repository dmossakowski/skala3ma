from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import uuid

@dataclass
class Route:
    """Domain model representing a single climbing route.

    Fields mirror existing dictionary keys used across the codebase so that
    replacing dict routes with `Route` instances is minimally invasive.
    Use `as_dict()` when a plain serializable representation is required
    (e.g. for JSON responses or compatibility with existing logic).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    routenum: str = ""
    line: str = ""
    colorfr: str = ""          # French color name (legacy UI field)
    color1: str = ""            # Primary color (hex or named)
    color2: str = ""            # Secondary color (unused currently)
    grade: str = ""             # Difficulty grade (e.g. '6b')
    color_modifier: str = "solid"  # Pattern modifier ('solid', 'marble', etc.)
    name: str = ""              # Human readable name
    openedby: str = ""          # Setter name
    opendate: str = ""          # Date opened (string format retained)
    notes: str = ""             # Setter notes

    @classmethod
    def create_dummy(cls, index: int, line: int, *, color: str, grade: str, modifier: str) -> "Route":
        return cls(
            routenum=str(index),
            line=str(line),
            colorfr="Vert",  # legacy, could map from color later
            color1=color,
            grade=grade,
            color_modifier=modifier,
            name=f"Route {index}",
        )

    def as_dict(self) -> Dict[str, Any]:
        """Return a dict representation compatible with existing code paths."""
        return {
            'id': self.id,
            'routenum': self.routenum,
            'line': self.line,
            'colorfr': self.colorfr,
            'color1': self.color1,
            'color2': self.color2,
            'grade': self.grade,
            'color_modifier': self.color_modifier,
            'name': self.name,
            'openedby': self.openedby,
            'opendate': self.opendate,
            'notes': self.notes,
        }

    def touch(self, **updates: Any) -> None:
        """Mutate selected attributes. Only existing attributes are updated."""
        for k, v in updates.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def __repr__(self) -> str:  # compact repr for debugging
        return f"Route(routenum={self.routenum}, grade={self.grade}, color1={self.color1}, name={self.name})"
