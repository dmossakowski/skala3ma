from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid


@dataclass
class Competition:
    """Domain model representing a competition.

    Mirrors the dictionary structure used across `competitionsEngine.py`.
    Use `as_dict()` to serialize for DB persistence and APIs.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    date: str = ""
    gym: str = ""
    gym_id: Optional[str] = None
    routesid: Optional[str] = None
    status: int = 0
    max_participants: int = 80
    results: Dict[str, Any] = field(default_factory=dict)
    calc_type: Any = 1
    competition_type: str = "adult"
    routes: List[Dict[str, Any]] = field(default_factory=list)
    instructions: str = ""
    added_by: Optional[str] = None

    # dynamic runtime fields
    climbers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    emails: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Competition":
        return cls(
            id=data.get('id') or uuid.uuid4().hex,
            name=data.get('name', ''),
            date=data.get('date', ''),
            gym=data.get('gym', ''),
            gym_id=data.get('gym_id'),
            routesid=data.get('routesid'),
            status=int(data.get('status', 0)),
            max_participants=int(data.get('max_participants', 80)),
            results=data.get('results', {}) or {},
            calc_type=data.get('calc_type', 1),
            competition_type=data.get('competition_type', "adult"),
            routes=data.get('routes', []) or [],
            instructions=data.get('instructions', ''),
            added_by=data.get('added_by'),
            climbers=data.get('climbers', {}) or {},
            emails=data.get('emails', []) or [],
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'date': self.date,
            'gym': self.gym,
            'gym_id': self.gym_id,
            'routesid': self.routesid,
            'status': self.status,
            'climbers': self.climbers,
            'max_participants': self.max_participants,
            'results': self.results,
            'calc_type': self.calc_type,
            'competition_type': self.competition_type,
            'routes': self.routes,
            'instructions': self.instructions,
            'added_by': self.added_by,
            'emails': self.emails,
        }

    def register_climber(self, climber: Dict[str, Any]) -> None:
        cid = climber.get('id') or uuid.uuid4().hex
        self.climbers[cid] = climber

    def set_status(self, status: int) -> None:
        self.status = status

    def update_routes(self, routes: List[Dict[str, Any]]) -> None:
        self.routes = routes or []

