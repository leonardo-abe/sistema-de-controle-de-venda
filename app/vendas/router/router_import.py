from typing import Any

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.shared.security.security import get_current_user
from app.shared.templates import templates
from app.vendas.router.dependencies import get_dashboard_service, get_import_service, get_repository_vendas
from app.vendas.repository.repository_vendas import RepositoryVendas
from app.vendas.service.service_import import ServiceImport

router = APIRouter(prefix="/importar", tags=["importacao"], dependencies=[Depends(get_current_user)])


@router.get("")
def import_page(
    request: Request,
    repository: RepositoryVendas = Depends(get_repository_vendas),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    batches = repository.list_batches()
    return templates.TemplateResponse(
        request,
        "importar.html",
        {"batches": batches, "resultado": None, "erro": None, "current_user": current_user},
    )


@router.post("")
def import_submit(
    request: Request,
    arquivo_pedidos: UploadFile = File(...),
    arquivo_pagamentos: UploadFile = File(...),
    arquivo_produtos: UploadFile = File(...),
    service: ServiceImport = Depends(get_import_service),
    repository: RepositoryVendas = Depends(get_repository_vendas),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    erro = None
    resultado = None
    try:
        resultado = service.importar(arquivo_pedidos, arquivo_pagamentos, arquivo_produtos)
    except Exception as exc:
        erro = getattr(exc, "detail", str(exc))

    batches = repository.list_batches()
    status_code = 400 if erro else 200
    return templates.TemplateResponse(
        request,
        "importar.html",
        {"batches": batches, "resultado": resultado, "erro": erro, "current_user": current_user},
        status_code=status_code,
    )
