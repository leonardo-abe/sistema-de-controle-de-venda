from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.shared.security.security import get_current_user
from app.shared.templates import templates
from app.vendas.dto.cliente_dto import ClientePaginaSchema
from app.vendas.router.dependencies import get_clientes_service
from app.vendas.service.service_clientes import ServiceClientes

router = APIRouter(prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_current_user)])


@router.get("")
def clientes_page(request: Request, current_user: dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse(request, "clientes.html", {"current_user": current_user})


@router.get("/api", response_model=ClientePaginaSchema)
def api_listar_clientes(
    busca: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    service: ServiceClientes = Depends(get_clientes_service),
):
    return service.listar(busca=busca, pagina=pagina)
