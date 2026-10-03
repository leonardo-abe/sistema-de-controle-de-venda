from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.shared.security.security import get_current_user
from app.shared.templates import templates
from app.vendas.dto.produto_dto import ProdutoPaginaSchema
from app.vendas.router.dependencies import get_produtos_service
from app.vendas.service.service_produtos import ServiceProdutos

router = APIRouter(prefix="/produtos", tags=["produtos"], dependencies=[Depends(get_current_user)])


@router.get("")
def produtos_page(request: Request, current_user: dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse(request, "produtos.html", {"current_user": current_user})


@router.get("/api", response_model=ProdutoPaginaSchema)
def api_listar_produtos(
    busca: str | None = Query(default=None),
    grupo: str | None = Query(default=None),
    marca: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    service: ServiceProdutos = Depends(get_produtos_service),
):
    return service.listar(busca=busca, grupo=grupo, marca=marca, pagina=pagina)


@router.get("/api/filtros")
def api_filtros_produtos(service: ServiceProdutos = Depends(get_produtos_service)):
    return service.opcoes_filtro()
