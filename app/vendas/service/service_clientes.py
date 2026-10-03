from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.vendas.dto.cliente_dto import ClienteListItemSchema, ClientePaginaSchema
from app.vendas.models import Pedido
from app.vendas.service.auditoria import flag_recuperado

POR_PAGINA_PADRAO = 20


class ServiceClientes:
    def __init__(self, session: Session) -> None:
        self.session = session

    def listar(self, busca: str | None, pagina: int, por_pagina: int = POR_PAGINA_PADRAO) -> ClientePaginaSchema:
        identificado = Pedido.cliente.is_not(None) & (Pedido.cliente != "")

        base = select(Pedido.cliente).where(identificado).distinct()
        if busca:
            base = base.where(Pedido.cliente.ilike(f"%{busca}%"))
        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        valor_total = func.coalesce(func.sum(Pedido.valor_liquido), 0.0)
        total_pedidos = func.count(Pedido.id)
        sinalizados = func.coalesce(func.sum(case((flag_recuperado(), 1), else_=0)), 0)

        stmt = (
            select(
                Pedido.cliente,
                total_pedidos,
                valor_total,
                func.max(Pedido.data),
                sinalizados,
            )
            .where(identificado)
            .group_by(Pedido.cliente)
            .order_by(valor_total.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        if busca:
            stmt = stmt.where(Pedido.cliente.ilike(f"%{busca}%"))

        rows = self.session.execute(stmt).all()
        itens = [
            ClienteListItemSchema(
                cliente=cliente,
                total_pedidos=qtd,
                valor_total=round(valor, 2),
                ticket_medio=round(valor / qtd, 2) if qtd else 0.0,
                ultima_compra=ultima,
                pedidos_sinalizados=sinal,
            )
            for cliente, qtd, valor, ultima, sinal in rows
        ]

        return ClientePaginaSchema(itens=itens, total=total, pagina=pagina, por_pagina=por_pagina)
