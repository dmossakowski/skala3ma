from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union
import uuid
from datetime import datetime
import re

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
    """A self-contained immutable-ish record of a route attempt.

    Flattened: embeds route metadata so Activity only stores List[RouteAttempt].
    Immutable route snapshot fields; only 'note' and 'user_grade' are mutable.
    """
    # Attempt identity / timing
    attempt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    attempt_time: Union[str, datetime] = field(default_factory=lambda: datetime.utcnow())
    status: str = "attempted"
    user_grade: Optional[str] = None
    note: str = ""

    # Route snapshot metadata
    route_id: str = ""
    routenum: str = ""
    line: str = ""
    colorfr: str = ""
    color1: str = ""
    color2: str = ""
    grade: str = ""
    color_modifier: str = "solid"
    name: str = ""
    openedby: str = ""
    opendate: str = ""
    notes: str = ""

    def __post_init__(self):
        # Normalize status
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
        # Basic validation hooks on embedded snapshot
        self._validate_color(self.color1)
        self._validate_grade(self.grade)
        if self.user_grade:
            self._validate_grade(self.user_grade)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteAttempt":
        """Rehydrate from dict (already flattened)."""
        return cls(
            attempt_id=data.get('attempt_id') or data.get('id') or uuid.uuid4().hex,
            attempt_time=data.get('attempt_time') or data.get('datetime') or datetime.utcnow(),
            status=data.get('status', 'attempted'),
            user_grade=data.get('user_grade') or data.get('user_proposed_grade'),
            note=data.get('note', ''),
            route_id=data.get('route_id') or data.get('id') or '',
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

    @classmethod
    def from_route_metadata(cls, route_meta: Dict[str, Any], *, status: str, user_grade: Optional[str] = None, note: str = "", attempt_time: Optional[Union[str, datetime]] = None) -> "RouteAttempt":
        """Create attempt from an external route metadata dict (already flattened)."""
        data = dict(route_meta)
        data.update({'status': status, 'user_grade': user_grade, 'note': note, 'attempt_time': attempt_time})
        return cls.from_dict(data)

    def as_dict(self) -> Dict[str, Any]:
        iso_time = self.attempt_time.isoformat(timespec='seconds') + "Z"
        return {
            'attempt_id': self.attempt_id,
            'attempt_time': iso_time,
            'status': self.status,
            'user_grade': self.user_grade,
            'note': self.note,
            # Embedded route snapshot
            'route_id': self.route_id,
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

    # legacy_flatten removed – new system uses lean attempts + separate route metadata

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
        if not self.user_grade or not self.grade:
            return 0
        return self._grade_order_key(self.user_grade) - self._grade_order_key(self.grade)

    def is_disagreement(self) -> bool:
        return bool(self.user_grade and self.grade and self.user_grade != self.grade)

    def to_route_update(self) -> Dict[str, Any]:
        return {
            'id': self.route_id,
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
        return f"RouteAttempt(route={self.routenum or self.route_id}, status={self.status}, user_grade={self.user_grade})"

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
    print("Attempt dict:", attempt.as_dict())
