from typing import Optional, List
from sqlalchemy.orm import Session
from ..repositories.route_repository import RouteRepository
from ..schemas.route import RouteCreate, RouteUpdate
from ..models.route import Route


class RouteService:
    def __init__(self):
        self.repository = RouteRepository()

    def get_route(self, db: Session, route_id: int) -> Optional[Route]:
        return self.repository.get(db, route_id)

    def get_route_by_name(self, db: Session, name: str) -> Optional[Route]:
        return self.repository.get_by_name(db, name=name)

    def get_routes(self, db: Session, skip: int = 0,
                   limit: int = 100) -> List[Route]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def get_active_routes(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100) -> List[Route]:
        return self.repository.get_active_routes(db, skip=skip, limit=limit)

    def search_routes_by_name(self, db: Session, name: str) -> List[Route]:
        return self.repository.search_by_name(db, name=name)

    def create_route(self, db: Session, route: RouteCreate) -> Route:
        # Check if route with name already exists
        if self.repository.get_by_name(db, name=route.name):
            raise ValueError("Route with this name already exists")

        return self.repository.create(db, obj_in=route)

    def update_route(
            self,
            db: Session,
            route_id: int,
            route_update: RouteUpdate) -> Optional[Route]:
        db_route = self.repository.get(db, route_id)
        if not db_route:
            return None

        update_data = route_update.model_dump(exclude_unset=True)

        # Check if name is being updated and if it already exists
        if "name" in update_data:
            existing_route = self.repository.get_by_name(
                db, name=update_data["name"])
            if existing_route and existing_route.id != route_id:
                raise ValueError("Route with this name already exists")

        return self.repository.update(db, db_obj=db_route, obj_in=update_data)

    def delete_route(self, db: Session, route_id: int) -> Optional[Route]:
        # Soft delete - just mark as inactive
        db_route = self.repository.get(db, route_id)
        if not db_route:
            return None

        return self.repository.update(
            db, db_obj=db_route, obj_in={
                "is_active": False})

    def reactivate_route(self, db: Session, route_id: int) -> Optional[Route]:
        db_route = self.repository.get(db, route_id)
        if not db_route:
            return None

        return self.repository.update(
            db, db_obj=db_route, obj_in={
                "is_active": True})
