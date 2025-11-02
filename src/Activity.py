from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .RouteAttempt import RouteAttempt


@dataclass
class Activity:
    """Represents a user activity/session at a gym.

    Mirrors the JSON schema:
    {
      "id": str,
      "gym_id": str,
      "routes_id": str,  # grouping container id for the route collection
      "starttime": str,  # original field name
      "name": str,       # activity name / description
      "gym_name": str,
      "routes": [ {route dicts...} ],
      "user_id": str,
      "date": str        # duplicate of starttime for convenience
    }
    """
    id: str
    gym_id: str
    routes_id: str
    starttime: str
    name: str = ""
    gym_name: str = ""
    user_id: str = ""
    date: str = ""  # may mirror starttime
    routes: List[Dict[str, Any]] = field(default_factory=list)  # legacy flattened dict form
    attempts: List[RouteAttempt] = field(default_factory=list)  # structured objects

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Activity":
        """Create an Activity from a JSON-like dict (tolerant to missing keys)."""
        instance = cls(
            id=data.get('id', ''),
            gym_id=str(data.get('gym_id', '')),
            routes_id=data.get('routes_id', ''),
            starttime=data.get('starttime') or data.get('date', ''),
            name=data.get('name', ''),
            gym_name=data.get('gym_name', ''),
            user_id=data.get('user_id', ''),
            date=data.get('date') or data.get('starttime', ''),
            routes=data.get('routes', [])
        )
        # build attempts from incoming route dicts if present
        for rdict in data.get('routes', []):
            try:
                instance.attempts.append(RouteAttempt.from_dict(rdict))
            except Exception as e:
                # tolerate malformed entries
                continue
        return instance

    def to_dict(self, *, legacy_flatten: bool = False) -> Dict[str, Any]:
        """Return dict representation.

        By default returns lean attempt objects (no duplicated route metadata) under 'attempts'
        plus a separate 'routes' collection of distinct route metadata.

        If legacy_flatten=True, returns the previous 'routes' list containing flattened entries.
        """
        if legacy_flatten:
            return {
                'id': self.id,
                'gym_id': self.gym_id,
                'routes_id': self.routes_id,
                'starttime': self.starttime,
                'name': self.name,
                'gym_name': self.gym_name,
                'routes': [a.legacy_flatten() for a in self.attempts] if self.attempts else self.routes,
                'user_id': self.user_id,
                'date': self.date or self.starttime,
            }
        # Build distinct route metadata set from attempts if available
        if self.attempts:
            # map by route id to avoid duplicates
            route_map: Dict[str, Dict[str, Any]] = {}
            for a in self.attempts:
                route_map[a.route.id] = a.route.as_dict()
            return {
                'id': self.id,
                'gym_id': self.gym_id,
                'routes_id': self.routes_id,
                'starttime': self.starttime,
                'name': self.name,
                'gym_name': self.gym_name,
                'routes': list(route_map.values()),
                'attempts': [a.as_dict() for a in self.attempts],
                'user_id': self.user_id,
                'date': self.date or self.starttime,
            }
        # Fallback: original structure if attempts absent
        return {
            'id': self.id,
            'gym_id': self.gym_id,
            'routes_id': self.routes_id,
            'starttime': self.starttime,
            'name': self.name,
            'gym_name': self.gym_name,
            'routes': self.routes,
            'attempts': [],
            'user_id': self.user_id,
            'date': self.date or self.starttime,
        }

    def add_route_attempt(self, attempt: RouteAttempt) -> None:
        """Add a structured attempt; legacy flattened list no longer updated automatically.
        Use to_dict(legacy_flatten=True) if old consumers require the merged representation."""
        self.attempts.append(attempt)

    def delete_route_attempt(self, attempt_id: str, *, remove_all: bool = False) -> bool:
        """Delete attempt(s) by attempt identifier (preferred) or fallback to route id if not matched.

        Parameters:
          attempt_id: identifier of the attempt (RouteAttempt.attempt_id) OR legacy route id.
          remove_all: when True and interpreting as route id, remove all attempts for that route.

        Behavior:
          - First pass tries to match attempt_id against RouteAttempt.attempt_id values (exact delete of those).
          - If no attempt_id matches and remove_all is True, will interpret attempt_id as a route id and remove all attempts for that route.
          - If no attempt_id matches and remove_all is False, will remove only the first attempt whose underlying route.id equals the provided id.

        Returns True if at least one attempt removed.
        Also prunes legacy flattened entries in self.routes accordingly.
        """
        if not attempt_id:
            return False
        removed = False

        # First try to remove by attempt_id (new behavior)
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
            # Fallback: treat provided id as route id
            route_id = attempt_id
            if self.attempts:
                new_attempts = []
                first_removed = False
                for att in self.attempts:
                    if att.route.id == route_id:
                        if remove_all:
                            removed = True
                            continue  # drop all matching
                        elif not first_removed:
                            first_removed = True
                            removed = True
                            continue  # drop first match only
                    new_attempts.append(att)
                self.attempts = new_attempts

        # Prune legacy flattened list
        if self.routes and removed:
            # Build a set of remaining (attempt) route ids to retain duplicates only for remaining attempts
            remaining_route_ids = {att.route.id for att in self.attempts}
            new_routes_legacy = []
            for r in self.routes:
                rid = r.get('id') or r.get('route_id')
                if rid in remaining_route_ids:
                    new_routes_legacy.append(r)
            self.routes = new_routes_legacy
        return removed

    def __str__(self) -> str:  # readable summary
        return f"Activity(id={self.id}, gym={self.gym_name or self.gym_id}, routes={len(self.routes)})"


# Example construction from the provided JSON
if __name__ == "__main__":
    sample = {"id": "ae4ffb9ec142494b989b5b06e015ddba", "gym_id": "1", "routes_id": "3f6dedd6eec94dccabe10c8b11116f79", "starttime": "2025-01-24", "name": "Rating activity", "gym_name": "Nanterre Grimpe", "routes": [{"id": "0a6a55e834a94e259b66d6bb05a2ee52", "routenum": "61", "line": "16", "colorfr": "#3399ff", "color1": "#3399ff", "color_modifier": "marble", "grade": "6b", "name": "", "openedby": "Franck ?", "opendate": "2023-07-01", "notes": "", "route_id": "5fd8336e-e02f-491a-b1ab-7165ef6175ae", "status": "climbed", "note": "", "user_grade": "6b"}, {"id": "cc257e7e19cf449f8d654df762fc7f8f", "routenum": "42", "line": "12", "colorfr": "#fe8839", "color1": "#fe8839", "color_modifier": "solid", "grade": "6a", "name": "Pozer", "openedby": "J\u00e9r\u00f4me", "opendate": "", "notes": "", "route_id": "665a8f8e-3b40-4213-a2e9-f04d8a743a1c", "status": "climbed", "note": "", "user_grade": "6a"}, {"id": "73ada3a3d9864eca91a31f657c5a9a82", "routenum": "43", "line": "12", "colorfr": "#ff0000", "color1": "#ff0000", "color_modifier": "marble", "grade": "6c", "name": "", "openedby": "J\u00e9r\u00f4me", "opendate": "", "notes": "Rouge marbr\u00e9", "route_id": "29b986b02d1441438aa84bb1a99f17de", "status": "climbed", "note": "", "user_grade": "6c"}, {"id": "c04e9d6bc5f84521ba603b53cdee0533", "routenum": "30", "line": "9", "colorfr": "#dd0808", "color1": "#dd0808", "color_modifier": "solid", "grade": "6b", "name": "Franc", "openedby": "J\u00e9r\u00f4me", "opendate": "2023-06-14", "notes": "", "route_id": "2dc65819-636a-4603-b9c7-daea89f019e0", "status": "climbed", "note": "", "user_grade": "6b"}, {"id": "3190f53e062c492b8ab503b79bc9f07f", "routenum": "36", "line": "10", "colorfr": "#0066cc", "color1": "#0066cc", "color_modifier": "solid", "grade": "6a", "name": "La bleusaille", "openedby": "Franck", "opendate": "2023-12-20", "notes": "environ 6A", "route_id": "36876ee1e53a4a3b9ae0d4a6adfd7f91", "status": "climbed", "note": "", "user_grade": "6a"}], "user_id": "c97a0f21-0f5e-4170-a4e2-d4d346dca815", "date": "2025-01-24"}
    act = Activity.from_json(sample)
    print(act)
    print(act.to_dict())
    # Demonstrate adding a new attempt
    if act.attempts:
        first = act.attempts[0]
        first.note = "Felt soft for the grade"
        print("After note mutation (lean):", act.to_dict()['attempts'][0])
        print("Legacy flattened snapshot:", act.to_dict(legacy_flatten=True)['routes'][0])




