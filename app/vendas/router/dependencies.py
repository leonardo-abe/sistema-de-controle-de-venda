from fastapi import Depends
from sqlalchemy.orm import Session

from app.infra.db.sqlite import get_session
from app.vendas.repository.repository_vendas import RepositoryVendas
from app.vendas.service.service_dashboard import ServiceDashboard
from app.vendas.service.service_import import ServiceImport


def get_repository_vendas(session: Session = Depends(get_session)) -> RepositoryVendas:
    return RepositoryVendas(session=session)


def get_import_service(repository: RepositoryVendas = Depends(get_repository_vendas)) -> ServiceImport:
    return ServiceImport(repository=repository)


def get_dashboard_service(session: Session = Depends(get_session)) -> ServiceDashboard:
    return ServiceDashboard(session=session)
