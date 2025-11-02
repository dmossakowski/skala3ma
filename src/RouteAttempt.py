from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union
import uuid
from datetime import datetime
import re

from .Route import Route

VALID_STATUSES = {"climbed", "flashed", "attempted"}
STATUS_SYNONYMS = {
    "send": "climbed",
    "sent": "climbed",
    "flash": "flashed",
    "try": "attempted",
    "attempt": "attempted",
}

@dataclass
class RouteAttempt:
    """Represents a single user interaction with a route inside an Activity (session).

    Composition:
      - route: the underlying Route definition (static metadata)
      - status: how the climber engaged with the route (climbed|flashed|attempted)
      - attempt_time: ISO8601 timestamp of the attempt (defaults to now if not provided)
      - user_grade: climber's proposed grade (may match or differ from route.grade)
      - note: optional per-attempt commentary

    Serialization helpers merge attempt data with route metadata to remain
    compatible with existing JSON shape used elsewhere in the app.
    """
    route: Route
    status: str
    attempt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    attempt_time: Union[str, datetime] = field(default_factory=lambda: datetime.utcnow())
    user_grade: Optional[str] = None
    note: str = ""

    def __post_init__(self):
        # Normalize status (case-insensitive + synonyms)
        raw = (self.status or "").strip().lower()
        raw = STATUS_SYNONYMS.get(raw, raw)
        if raw not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {VALID_STATUSES} (supports synonyms {list(STATUS_SYNONYMS.keys())}).")
        self.status = raw
        # Ensure attempt_time is datetime internally
        if isinstance(self.attempt_time, str):
            try:
                # Accept ISO-like date/time or date-only; fallback to now
                self.attempt_time = datetime.fromisoformat(self.attempt_time.replace("Z",""))
            except Exception:
                self.attempt_time = datetime.utcnow()
        # Basic validation hooks
        self._validate_color(self.route.color1)
        self._validate_grade(self.route.grade)
        if self.user_grade:
            self._validate_grade(self.user_grade)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteAttempt":
        """Create a RouteAttempt from a dict in the existing flattened route attempt shape.
        Expected keys (subset tolerated):
          id, routenum, line, colorfr, color1, color2, grade, color_modifier, name,
          openedby, opendate, notes, route_id, status, note, user_grade, datetime/attempt_time
        """
        # Build Route first from route metadata
        route = Route(
            id=data.get('id', data.get('route_id', '')),
            routenum=str(data.get('routenum', '')),
            line=str(data.get('line', '')),
            colorfr=data.get('colorfr', ''),
            color1=data.get('color1', ''),
            color2=data.get('color2', ''),
            grade=data.get('grade', ''),
            color_modifier=data.get('color_modifier', 'solid'),
            name=data.get('name', ''),
            openedby=data.get('openedby', ''),
            opendate=data.get('opendate', ''),
            notes=data.get('notes', ''),
        )
        attempt_time = data.get('attempt_time') or data.get('datetime') or datetime.utcnow()
        return cls(
            route=route,
            attempt_id=data.get('attempt_id') or data.get('id_attempt') or uuid.uuid4().hex,
            status=data.get('status', 'attempted'),
            attempt_time=attempt_time,
            user_grade=data.get('user_grade') or data.get('user_proposed_grade'),
            note=data.get('note', ''),
        )

    @classmethod
    def from_route(cls, route: Route, *, status: str, user_grade: Optional[str] = None, note: str = "", attempt_time: Optional[Union[str, datetime]] = None) -> "RouteAttempt":
        """Create an attempt from an existing Route instance."""
        return cls(
            route=route,
            status=status,
            attempt_time=attempt_time or datetime.utcnow(),
            user_grade=user_grade,
            note=note,
        )

    def as_dict(self) -> Dict[str, Any]:
        """Return lean attempt representation referencing route id only (no duplicated route fields)."""
        iso_time = self.attempt_time.isoformat(timespec='seconds') + "Z"
        return {
            'attempt_id': self.attempt_id,
            'route_id': self.route.id,
            'status': self.status,
            'user_grade': self.user_grade,
            'note': self.note,
            'attempt_time': iso_time,
        }

    def legacy_flatten(self) -> Dict[str, Any]:
        """Return previous flattened representation (route metadata + attempt fields) for backward compatibility."""
        base = self.route.as_dict()
        base.update(self.as_dict())
        return base

    # ----- Utility & Analysis Methods -----
    @staticmethod
    def _grade_order_key(grade: str) -> int:
        """Convert common French grades (and variations) into an ordering integer.
        Supports patterns like 4a, 5c+, 6a, 6a+, 6b, 6c, 7a, 7a+, etc.
        Non-matching grades get a large fallback value to avoid crashes."""
        if not grade:
            return 0
        pattern = r"^(\d)([abc])(\+?)$"
        m = re.match(pattern, grade.strip().lower())
        if not m:
            # attempt partial mapping (e.g. '6' or '6a/b'): very coarse
            digits = re.findall(r"\d", grade)
            return int(digits[0]) * 100 if digits else 9999
        number, letter, plus = m.groups()
        base = int(number) * 100
        letter_map = {'a': 0, 'b': 1, 'c': 2}
        base += letter_map[letter] * 10
        if plus:
            base += 5
        return base

    def grade_diff(self) -> int:
        """Return user_grade - route.grade ordering difference (positive means proposed harder)."""
        if not self.user_grade or not self.route.grade:
            return 0
        return self._grade_order_key(self.user_grade) - self._grade_order_key(self.route.grade)

    def is_disagreement(self) -> bool:
        return bool(self.user_grade and self.route.grade and self.user_grade != self.route.grade)

    def to_route_update(self) -> Dict[str, Any]:
        """Return a dict of route fields that could be updated based on attempt (e.g. user_grade consensus)."""
        return {
            'id': self.route.id,
            'proposed_grade': self.user_grade,
            'note_append': self.note.strip() or None,
        }

    @staticmethod
    def _validate_color(color: str) -> None:
        if not color:
            return
        if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", color):
            # Non-hex values tolerated; could raise if stricter needed
            pass

    @staticmethod
    def _validate_grade(grade: str) -> None:
        if not grade:
            return
        if not re.match(r"^\d[abc](\+)?$", grade.lower()):
            # Accept but don't raise; change to raise ValueError for strictness
            pass

    def __repr__(self) -> str:
        return f"RouteAttempt(route={self.route.routenum or self.route.id}, status={self.status}, user_grade={self.user_grade})"

# Quick self-test
if __name__ == "__main__":
    sample = {
        'id': '0a6a55e834a94e259b66d6bb05a2ee52',
        'routenum': '61',
        'line': '16',
        'colorfr': '#3399ff',
        'color1': '#3399ff',
        'color_modifier': 'marble',
        'grade': '6b',
        'openedby': 'Franck ?',
        'opendate': '2023-07-01',
        'notes': '',
        'route_id': '5fd8336e-e02f-491a-b1ab-7165ef6175ae',
        'status': 'climbed',
        'note': '',
        'user_grade': '6b'
    }
    attempt = RouteAttempt.from_dict(sample)
    print(attempt)
    print("Lean attempt:", attempt.as_dict())
    print("Legacy flattened:", attempt.legacy_flatten())
