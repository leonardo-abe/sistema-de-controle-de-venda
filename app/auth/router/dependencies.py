from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.repository.repository_user import RepositoryUser
from app.auth.service.service_auth import ServiceAuth
from app.auth.service.service_user import ServiceUser
from app.infra.db.sqlite import get_session


def get_repository_user(session: Session = Depends(get_session)) -> RepositoryUser:
    return RepositoryUser(session=session)


def get_auth_service(repository: RepositoryUser = Depends(get_repository_user)) -> ServiceAuth:
    return ServiceAuth(repository=repository)


def get_user_service(repository: RepositoryUser = Depends(get_repository_user)) -> ServiceUser:
    return ServiceUser(repository=repository)
