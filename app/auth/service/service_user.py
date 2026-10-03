from fastapi import HTTPException, status

from app.auth.dto.user_dto import UserCreateSchema, UserUpdateSchema
from app.auth.interface.irepository_user import UserRepositoryProtocol
from app.auth.models import User
from app.shared.security.security import hash_password


class ServiceUser:
    def __init__(self, repository: UserRepositoryProtocol) -> None:
        self.repository = repository

    def list_users(self) -> list[User]:
        return self.repository.list_all()

    def create_user(self, data: UserCreateSchema) -> User:
        if self.repository.get_by_email(data.email) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe um usuario com este email")

        user = User(
            name=data.name,
            email=data.email,
            role=data.role,
            hashed_password=hash_password(data.password),
        )
        return self.repository.create(user)

    def update_user(self, user_id: int, data: UserUpdateSchema) -> User:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

        if data.name is not None:
            user.name = data.name
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password:
            user.hashed_password = hash_password(data.password)

        return self.repository.update(user)

    def delete_user(self, user_id: int, current_user_id: int) -> None:
        if user_id == current_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voce nao pode remover o proprio usuario")

        user = self.repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

        self.repository.delete(user)
