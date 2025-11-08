from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
import uuid

from .RouteAttempt import RouteAttempt


@dataclass
class Activity:
    """Represents a user activity/session storing ONLY flattened RouteAttempt objects.

    JSON schema:
    {
      "id": str,
      "gym_id": str,
      "starttime": str,
      "name": str,
      "gym_name": str,
      "attempts": [ { RouteAttempt.as_dict() } ],
      "user_id": str,
      "date": str
    }
    Legacy shapes with 'routes' or 'routes_dict' are migrated into attempts.
    """
    id: str
    gym_id: str
    routes_id: str  # retained for backward compatibility / grouping id
    starttime: str
    name: str = ""
    gym_name: str = ""
    user_id: str = ""
    date: str = ""  # may mirror starttime
    attempts: List[RouteAttempt] = field(default_factory=list)


    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Activity":
        """Create an Activity from JSON, normalizing to attempts-only form."""
        instance = cls(
            id=data.get('id', ''),
            gym_id=str(data.get('gym_id', '')),
            routes_id=data.get('routes_id', ''),
            starttime=data.get('starttime') or data.get('date', ''),
            name=data.get('name', ''),
            gym_name=data.get('gym_name', ''),
            user_id=data.get('user_id', ''),
            date=data.get('date') or data.get('starttime', ''),
        )
        # Preferred new shape: already has attempts list of flattened dicts
        if isinstance(data.get('attempts'), list):
            for adict in data['attempts']:
                if isinstance(adict, dict):
                    try:
                        instance.attempts.append(RouteAttempt.from_dict(adict))
                    except Exception:
                        continue
            return instance
        # Legacy flattened 'routes' list containing mixed metadata + attempt fields
        legacy = data.get('routes', [])
        for r in legacy:
            if not isinstance(r, dict):
                continue
            try:
                # Ensure attempt_id present
                if 'attempt_id' not in r:
                    r['attempt_id'] = r.get('attempt_id') or r.get('id') or uuid.uuid4().hex
                if 'route_id' not in r:
                    r['route_id'] = r.get('route_id') or r.get('id') or ''
                instance.attempts.append(RouteAttempt.from_dict(r))
            except Exception:
                continue
        return instance


    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'gym_id': self.gym_id,
            'routes_id': self.routes_id,
            'starttime': self.starttime,
            'name': self.name,
            'gym_name': self.gym_name,
            'attempts': [a.as_dict() for a in self.attempts],
            'user_id': self.user_id,
            'date': self.date or self.starttime,
        }

    def add_route_attempt(self, attempt: RouteAttempt) -> None:
        self.attempts.append(attempt)

    def delete_route_attempt(self, attempt_id: str, *, remove_all: bool = False) -> bool:
        """Delete attempt(s) by attempt_id or fallback to route_id if no attempt id matches.

        Parameters:
          attempt_id: attempt identifier OR (legacy) a route_id to target attempts for that route.
          remove_all: if treating as route_id, remove all attempts for that route when True

        Returns True if at least one attempt removed.
        """
        if not attempt_id:
            return False
        removed = False

        # First try to remove by attempt_id
        new_attempts: List[RouteAttempt] = []
        for att in self.attempts:
            if att.attempt_id == attempt_id:
                removed = True
                if not remove_all:
                    # skip exactly one attempt id and keep rest
                    continue
                else:
                    # remove all attempts that share this attempt_id (should normally be unique)
                    continue
            new_attempts.append(att)

        if removed:
            self.attempts = new_attempts
        else:
            # Fallback: treat provided value as route_id
            route_id = attempt_id
            if self.attempts:
                new_attempts = []
                first_removed = False
                for att in self.attempts:
                    if att.route_id == route_id:
                        if remove_all:
                            removed = True
                            continue  # drop all matching
                        elif not first_removed:
                            first_removed = True
                            removed = True
                            continue  # drop first match only
                    new_attempts.append(att)
                self.attempts = new_attempts

        return removed

    def __str__(self) -> str:  # readable summary
        return f"Activity(id={self.id}, gym={self.gym_name or self.gym_id}, attempts={len(self.attempts)})"


# Example construction from the provided JSON
if __name__ == "__main__":
    sample = {"id": "act123", "gym_id": "1", "routes_id": "legacyset", "starttime": "2025-01-24", "name": "Rating activity", "gym_name": "Nanterre Grimpe", "routes": [{"id": "0a6a55e834a94e259b66d6bb05a2ee52", "routenum": "61", "line": "16", "colorfr": "#3399ff", "color1": "#3399ff", "color_modifier": "marble", "grade": "6b", "openedby": "Franck ?", "opendate": "2023-07-01", "notes": "", "route_id": "5fd8336e-e02f-491a-b1ab-7165ef6175ae", "status": "climbed", "note": "", "user_grade": "6b"}]}
    act = Activity.from_json(sample)
    print(act)
    print(act.to_dict())
    # Demonstrate adding a new attempt
    if act.attempts:
        first = act.attempts[0]
        first.note = "Felt soft for the grade"
        print("After note mutation (lean):", act.to_dict()['attempts'][0])
        # Legacy flattened no longer generated; new structure only




