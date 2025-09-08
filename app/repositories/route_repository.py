from typing import Optional, List
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.route import Route
from ..schemas.route import RouteCreate, RouteUpdate


class RouteRepository(BaseRepository[Route, RouteCreate, RouteUpdate]):
    def __init__(self):
        super().__init__(Route)

    def get_by_name(self, db: Session, *, name: str) -> Optional[Route]:
        return db.query(Route).filter(Route.name == name).first()

    def get_active_routes(
            self,
            db: Session,
            *,
            skip: int = 0,
            limit: int = 100) -> List[Route]:
        return db.query(Route).filter(
            Route.is_active).offset(skip).limit(limit).all()

    def search_by_name(self, db: Session, *, name: str) -> List[Route]:
        return db.query(Route).filter(Route.name.ilike(f"%{name}%")).all()

    def deactivate_route(
            self,
            db: Session,
            *,
            route_id: int) -> Optional[Route]:
        route = self.get(db, route_id)
        if route:
            route.is_active = False
            db.commit()
            db.refresh(route)
        return route
