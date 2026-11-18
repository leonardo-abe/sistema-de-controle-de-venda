from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.shared.security.security import get_current_user
from app.shared.templates import templates
from app.vendas.router.dependencies import get_dashboard_service
from app.vendas.service.service_dashboard import FiltrosDashboard, ServiceDashboard

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/")
def dashboard_page(request: Request, current_user: dict[str, Any] = Depends(get_current_user)):
    return templates.TemplateResponse(request, "dashboard.html", {"current_user": current_user})


def _periodo_anterior(data_inicio: date | None, data_fim: date | None) -> tuple[date, date] | None:
    if data_inicio is None or data_fim is None:
        return None
    duracao = (data_fim - data_inicio).days + 1
    anterior_fim = data_inicio - timedelta(days=1)
    anterior_inicio = anterior_fim - timedelta(days=duracao - 1)
    return anterior_inicio, anterior_fim


@router.get("/api/dashboard/filtros")
def api_filtros(service: ServiceDashboard = Depends(get_dashboard_service)):
    return service.opcoes_filtro()


@router.get("/api/dashboard/resumo")
def api_resumo(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    vendedor: str | None = Query(default=None),
    forma_pagamento: str | None = Query(default=None),
    service: ServiceDashboard = Depends(get_dashboard_service),
):
    filtros = FiltrosDashboard(
        data_inicio=data_inicio,
        data_fim=data_fim,
        vendedor=vendedor or None,
        forma_pagamento=forma_pagamento or None,
    )

    periodo_anterior = _periodo_anterior(data_inicio, data_fim)
    filtros_anterior = (
        FiltrosDashboard(data_inicio=periodo_anterior[0], data_fim=periodo_anterior[1], vendedor=filtros.vendedor, forma_pagamento=filtros.forma_pagamento)
        if periodo_anterior
        else None
    )
    kpis_anterior = service.kpis(filtros_anterior) if filtros_anterior else None

    return {
        "kpis": service.kpis(filtros),
        "kpis_anterior": kpis_anterior,
        "vendas_por_dia": service.vendas_por_dia(filtros),
        "vendas_por_vendedor": service.vendas_por_vendedor(filtros),
        "formas_pagamento": service.formas_pagamento(filtros),
        "top_produtos": service.top_produtos(filtros),
        "top_grupos": service.top_grupos(filtros),
        "margem_por_grupo": service.margem_por_grupo(filtros),
        "pedidos_por_cidade": service.pedidos_por_cidade(filtros),
        "identificacao_cliente": service.identificacao_cliente(filtros),
        "auditoria_resumo": service.auditoria_resumo(filtros),
        "auditoria_por_vendedor": service.auditoria_por_vendedor(filtros),
        "auditoria_pedidos": service.auditoria_pedidos(filtros),
    }
