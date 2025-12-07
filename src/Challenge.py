from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid


@dataclass
class Challenge:
    """Represents a sub-event or challenge associated with a gym or competition.

    A Challenge can define its own set of routes and rules independent of
    a competition. Designed for future persistence in `skala_db.py`.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    gym_id: Optional[str] = None
    competition_id: Optional[str] = None
    name: str = ""
    description: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    routesid: Optional[str] = None
    routes: List[Dict[str, Any]] = field(default_factory=list)
    status: int = 0
    created_by: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Challenge":
        return cls(
            id=data.get('id') or uuid.uuid4().hex,
            gym_id=data.get('gym_id'),
            competition_id=data.get('competition_id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            routesid=data.get('routesid'),
            routes=data.get('routes', []) or [],
            status=int(data.get('status', 0)),
            created_by=data.get('created_by'),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'gym_id': self.gym_id,
            'competition_id': self.competition_id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'routesid': self.routesid,
            'routes': self.routes,
            'status': self.status,
            'created_by': self.created_by,
        }

    def set_status(self, status: int) -> None:
        self.status = status

    def update_routes(self, routes: List[Dict[str, Any]]) -> None:
        self.routes = routes or []

