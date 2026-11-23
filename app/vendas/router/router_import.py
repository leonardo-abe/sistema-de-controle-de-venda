from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse

from app.shared.security.security import get_current_user, require_admin
from app.shared.templates import templates
from app.vendas.router.dependencies import get_dashboard_service, get_import_service, get_repository_vendas
from app.vendas.repository.repository_vendas import RepositoryVendas
from app.vendas.service.service_import import ServiceImport

router = APIRouter(prefix="/importar", tags=["importacao"], dependencies=[Depends(get_current_user)])


@router.get("")
def import_page(
    request: Request,
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    loja: str | None = Query(default=None),
    repository: RepositoryVendas = Depends(get_repository_vendas),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    # O select de loja manda "" quando "Todas" esta selecionado - Query(int)
    # rejeitaria essa string vazia direto, por isso o parametro chega como
    # str e e convertido aqui.
    loja = int(loja) if loja else None
    batches = repository.list_batches(data_inicio=data_inicio, data_fim=data_fim, loja=loja)
    lojas_disponiveis = repository.list_lojas_distintas()
    total_pendencias = len(repository.list_pendencias_nao_resolvidas())
    return templates.TemplateResponse(
        request,
        "importar.html",
        {
            "batches": batches,
            "lojas_disponiveis": lojas_disponiveis,
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
            "filtro_loja": loja,
            "resultado": None,
            "erro": None,
            "current_user": current_user,
            "total_pendencias": total_pendencias,
        },
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
    lojas_disponiveis = repository.list_lojas_distintas()
    total_pendencias = len(repository.list_pendencias_nao_resolvidas())
    status_code = 400 if erro else 200
    return templates.TemplateResponse(
        request,
        "importar.html",
        {
            "batches": batches,
            "lojas_disponiveis": lojas_disponiveis,
            "filtro_data_inicio": None,
            "filtro_data_fim": None,
            "filtro_loja": None,
            "resultado": resultado,
            "erro": erro,
            "current_user": current_user,
            "total_pendencias": total_pendencias,
        },
        status_code=status_code,
    )


@router.post("/{batch_id}/excluir")
def excluir_batch(
    batch_id: int,
    repository: RepositoryVendas = Depends(get_repository_vendas),
):
    repository.delete_batch_data(batch_id)
    return RedirectResponse(url="/importar", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/pendencias")
def pendencias_page(
    request: Request,
    loja: str | None = Query(default=None),
    service: ServiceImport = Depends(get_import_service),
    repository: RepositoryVendas = Depends(get_repository_vendas),
    current_user: dict[str, Any] = Depends(require_admin),
):
    loja = int(loja) if loja else None
    pendencias = repository.list_pendencias_nao_resolvidas(loja=loja)
    comparacoes = [service.montar_comparacao(p) for p in pendencias]
    lojas_disponiveis = repository.list_lojas_distintas()
    return templates.TemplateResponse(
        request,
        "pendencias.html",
        {
            "comparacoes": comparacoes,
            "lojas_disponiveis": lojas_disponiveis,
            "filtro_loja": loja,
            "current_user": current_user,
        },
    )


@router.post("/pendencias/{pendencia_id}/resolver")
def resolver_pendencia(
    pendencia_id: int,
    usar_novo: bool = Form(...),
    service: ServiceImport = Depends(get_import_service),
    current_user: dict[str, Any] = Depends(require_admin),
):
    service.resolver_pendencia(pendencia_id, usar_novo)
    return RedirectResponse(url="/importar/pendencias", status_code=status.HTTP_303_SEE_OTHER)
