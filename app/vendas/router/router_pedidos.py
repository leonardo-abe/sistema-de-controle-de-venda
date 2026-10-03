from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.shared.security.security import get_current_user
from app.shared.templates import templates
from app.vendas.dto.pedido_dto import PedidoDetalheSchema, PedidoPaginaSchema
from app.vendas.router.dependencies import get_pedidos_service
from app.vendas.service.service_pedidos import ServicePedidos

router = APIRouter(prefix="/pedidos", tags=["pedidos"], dependencies=[Depends(get_current_user)])


@router.get("")
def pedidos_page(request: Request, current_user: dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse(request, "pedidos.html", {"current_user": current_user})


@router.get("/api", response_model=PedidoPaginaSchema)
def api_listar_pedidos(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    vendedor: str | None = Query(default=None),
    forma_pagamento: str | None = Query(default=None),
    busca: str | None = Query(default=None),
    apenas_sinalizados: bool = Query(default=False),
    pagina: int = Query(default=1, ge=1),
    service: ServicePedidos = Depends(get_pedidos_service),
):
    return service.listar(
        data_inicio=data_inicio,
        data_fim=data_fim,
        vendedor=vendedor or None,
        forma_pagamento=forma_pagamento or None,
        busca=busca or None,
        apenas_sinalizados=apenas_sinalizados,
        pagina=pagina,
    )


@router.get("/api/{loja}/{pedido}", response_model=PedidoDetalheSchema)
def api_detalhe_pedido(loja: int, pedido: int, service: ServicePedidos = Depends(get_pedidos_service)):
    return service.detalhe(loja=loja, pedido=pedido)


@router.get("/{loja}/{pedido}")
def pedido_detalhe_page(
    loja: int,
    pedido: int,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request,
        "pedido_detalhe.html",
        {"current_user": current_user, "loja": loja, "pedido": pedido},
    )
