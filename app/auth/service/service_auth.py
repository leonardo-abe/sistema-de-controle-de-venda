from fastapi import HTTPException, status

from app.auth.interface.irepository_user import UserRepositoryProtocol
from app.shared.security.security import create_access_token, verify_password


class ServiceAuth:
    def __init__(self, repository: UserRepositoryProtocol) -> None:
        self.repository = repository

    def login(self, email: str, password: str) -> str:
        user = self.repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha invalidos")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desativado")

        return create_access_token({"sub": str(user.id), "email": user.email, "name": user.name, "role": user.role})
