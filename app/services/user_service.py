from typing import Optional, List
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ..repositories.user_repository import UserRepository
from ..schemas.user import UserCreate, UserUpdate, UserResponse
from ..models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self):
        self.repository = UserRepository()

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        return self.repository.get(db, user_id)

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return self.repository.get_by_email(db, email=email)

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return self.repository.get_by_username(db, username=username)

    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def create_user(self, db: Session, user: UserCreate) -> User:
        # Check if user already exists
        if self.repository.get_by_email(db, email=user.email):
            raise ValueError("Email already registered")
        if self.repository.get_by_username(db, username=user.username):
            raise ValueError("Username already taken")
        
        # Hash password and prepare user data
        hashed_password = self.get_password_hash(user.password)
        user_data = user.model_dump()
        user_data["hashed_password"] = hashed_password
        del user_data["password"]
        
        # Create user directly with the prepared data
        db_obj = User(**user_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_user(self, db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        db_user = self.repository.get(db, user_id)
        if not db_user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data:
            update_data["hashed_password"] = self.get_password_hash(update_data["password"])
            del update_data["password"]
        
        return self.repository.update(db, db_obj=db_user, obj_in=update_data)

    def delete_user(self, db: Session, user_id: int) -> Optional[User]:
        return self.repository.remove(db, id=user_id)

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        user = self.repository.get_by_email(db, email=email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user 