from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.vendas.dto.dashboard_dto import (
    AuditoriaResumoSchema,
    KpiResumoSchema,
    PedidoAuditoriaSchema,
    SerieDuplaSchema,
    SeriePontoSchema,
)
from app.vendas.models import ItemVenda, Pagamento, Pedido, Produto

TOP_N = 10
LIMITE_AUDITORIA = 50
DESCONTO_ALTO_PCT = 50.0


@dataclass(frozen=True)
class FiltrosDashboard:
    data_inicio: date | None = None
    data_fim: date | None = None
    vendedor: str | None = None
    forma_pagamento: str | None = None


class ServiceDashboard:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _filtrar_periodo[T](stmt: Select[T], coluna, data_inicio: date | None, data_fim: date | None) -> Select[T]:
        if data_inicio is not None:
            stmt = stmt.where(coluna >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(coluna <= data_fim)
        return stmt

    @staticmethod
    def _pedido_tem_pagamento(loja_col, pedido_col, tipo: str):
        return (
            select(Pagamento.id)
            .where(Pagamento.loja == loja_col, Pagamento.pedido == pedido_col, Pagamento.tipo_pagamento == tipo)
            .exists()
        )

    @staticmethod
    def _pedido_do_vendedor(loja_col, pedido_col, vendedor: str):
        return (
            select(Pedido.id)
            .where(Pedido.loja == loja_col, Pedido.pedido == pedido_col, Pedido.vendedor == vendedor)
            .exists()
        )

    @staticmethod
    def _flag_recuperado():
        situacao_preenchida = Pedido.situacao.is_not(None) & (Pedido.situacao != "")
        return situacao_preenchida | (Pedido.perc_desconto >= DESCONTO_ALTO_PCT)

    def _aplicar_filtros_pedido[T](self, stmt: Select[T], f: FiltrosDashboard) -> Select[T]:
        stmt = self._filtrar_periodo(stmt, Pedido.data, f.data_inicio, f.data_fim)
        if f.vendedor:
            stmt = stmt.where(Pedido.vendedor == f.vendedor)
        if f.forma_pagamento:
            stmt = stmt.where(self._pedido_tem_pagamento(Pedido.loja, Pedido.pedido, f.forma_pagamento))
        return stmt

    def _aplicar_filtros_item[T](self, stmt: Select[T], f: FiltrosDashboard) -> Select[T]:
        stmt = self._filtrar_periodo(stmt, ItemVenda.data, f.data_inicio, f.data_fim)
        if f.vendedor:
            stmt = stmt.where(self._pedido_do_vendedor(ItemVenda.loja, ItemVenda.pedido, f.vendedor))
        if f.forma_pagamento:
            stmt = stmt.where(self._pedido_tem_pagamento(ItemVenda.loja, ItemVenda.pedido, f.forma_pagamento))
        return stmt

    def _aplicar_filtros_pagamento[T](self, stmt: Select[T], f: FiltrosDashboard) -> Select[T]:
        stmt = self._filtrar_periodo(stmt, Pagamento.data, f.data_inicio, f.data_fim)
        if f.vendedor:
            stmt = stmt.where(self._pedido_do_vendedor(Pagamento.loja, Pagamento.pedido, f.vendedor))
        if f.forma_pagamento:
            stmt = stmt.where(Pagamento.tipo_pagamento == f.forma_pagamento)
        return stmt

    def opcoes_filtro(self) -> dict[str, list[str]]:
        vendedor = func.coalesce(Pedido.vendedor, "NAO INFORMADO")
        vendedores = self.session.execute(select(vendedor).distinct().order_by(vendedor)).scalars().all()
        formas = (
            self.session.execute(select(Pagamento.tipo_pagamento).distinct().order_by(Pagamento.tipo_pagamento))
            .scalars()
            .all()
        )
        return {"vendedores": list(vendedores), "formas_pagamento": list(formas)}

    def kpis(self, f: FiltrosDashboard) -> KpiResumoSchema:
        stmt = select(
            func.count(Pedido.id),
            func.coalesce(func.sum(Pedido.valor_liquido), 0.0),
            func.coalesce(func.sum(Pedido.valor_desconto), 0.0),
        )
        stmt = self._aplicar_filtros_pedido(stmt, f)
        total_pedidos, valor_total_liquido, total_desconto = self.session.execute(stmt).one()

        stmt_itens = select(
            func.coalesce(func.sum(ItemVenda.quantidade), 0.0),
            func.coalesce(func.sum(ItemVenda.valor_total - ItemVenda.custo), 0.0),
        )
        stmt_itens = self._aplicar_filtros_item(stmt_itens, f)
        total_itens_vendidos, margem_bruta = self.session.execute(stmt_itens).one()

        ticket_medio = (valor_total_liquido / total_pedidos) if total_pedidos else 0.0

        return KpiResumoSchema(
            total_pedidos=total_pedidos,
            valor_total_liquido=round(valor_total_liquido, 2),
            ticket_medio=round(ticket_medio, 2),
            total_desconto=round(total_desconto, 2),
            total_itens_vendidos=round(total_itens_vendidos, 2),
            margem_bruta=round(margem_bruta, 2),
        )

    def vendas_por_dia(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        stmt = select(Pedido.data, func.coalesce(func.sum(Pedido.valor_liquido), 0.0)).group_by(Pedido.data).order_by(Pedido.data)
        stmt = self._aplicar_filtros_pedido(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=str(dia), valor=round(valor, 2)) for dia, valor in rows]

    def vendas_por_vendedor(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        vendedor = func.coalesce(Pedido.vendedor, "NAO INFORMADO")
        stmt = (
            select(vendedor, func.coalesce(func.sum(Pedido.valor_liquido), 0.0))
            .group_by(vendedor)
            .order_by(func.sum(Pedido.valor_liquido).desc())
            .limit(TOP_N)
        )
        stmt = self._aplicar_filtros_pedido(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=nome, valor=round(valor, 2)) for nome, valor in rows]

    def formas_pagamento(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        stmt = (
            select(Pagamento.tipo_pagamento, func.coalesce(func.sum(Pagamento.valor), 0.0))
            .group_by(Pagamento.tipo_pagamento)
            .order_by(func.sum(Pagamento.valor).desc())
        )
        stmt = self._aplicar_filtros_pagamento(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=tipo, valor=round(valor, 2)) for tipo, valor in rows]

    def top_produtos(self, f: FiltrosDashboard) -> list[SerieDuplaSchema]:
        stmt = (
            select(
                Produto.nome,
                func.coalesce(func.sum(ItemVenda.valor_total), 0.0),
                func.coalesce(func.sum(ItemVenda.quantidade), 0.0),
            )
            .join(Produto, Produto.cod_prod == ItemVenda.cod_prod)
            .group_by(Produto.nome)
            .order_by(func.sum(ItemVenda.valor_total).desc())
            .limit(TOP_N)
        )
        stmt = self._aplicar_filtros_item(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SerieDuplaSchema(chave=nome, valor=round(valor, 2), valor_secundario=round(qtd, 2)) for nome, valor, qtd in rows]

    def top_grupos(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        grupo = func.coalesce(Produto.grupo, "SEM GRUPO")
        stmt = (
            select(grupo, func.coalesce(func.sum(ItemVenda.valor_total), 0.0))
            .join(Produto, Produto.cod_prod == ItemVenda.cod_prod)
            .group_by(grupo)
            .order_by(func.sum(ItemVenda.valor_total).desc())
            .limit(TOP_N)
        )
        stmt = self._aplicar_filtros_item(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=nome, valor=round(valor, 2)) for nome, valor in rows]

    def margem_por_grupo(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        grupo = func.coalesce(Produto.grupo, "SEM GRUPO")
        stmt = (
            select(grupo, func.coalesce(func.sum(ItemVenda.valor_total - ItemVenda.custo), 0.0))
            .join(Produto, Produto.cod_prod == ItemVenda.cod_prod)
            .group_by(grupo)
            .order_by(func.sum(ItemVenda.valor_total - ItemVenda.custo).desc())
            .limit(TOP_N)
        )
        stmt = self._aplicar_filtros_item(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=nome, valor=round(valor, 2)) for nome, valor in rows]

    def pedidos_por_cidade(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        cidade = func.coalesce(Pedido.cidade, "NAO INFORMADA")
        stmt = (
            select(cidade, func.count(Pedido.id))
            .group_by(cidade)
            .order_by(func.count(Pedido.id).desc())
            .limit(TOP_N)
        )
        stmt = self._aplicar_filtros_pedido(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=nome, valor=float(qtd)) for nome, qtd in rows]

    def identificacao_cliente(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        identificado = (Pedido.cliente.is_not(None)) & (Pedido.cliente != "")
        stmt = select(identificado, func.count(Pedido.id)).group_by(identificado)
        stmt = self._aplicar_filtros_pedido(stmt, f)
        rows = self.session.execute(stmt).all()
        resultado = {"Identificado": 0.0, "Nao identificado": 0.0}
        for is_identificado, qtd in rows:
            chave = "Identificado" if is_identificado else "Nao identificado"
            resultado[chave] = float(qtd)
        return [SeriePontoSchema(chave=chave, valor=valor) for chave, valor in resultado.items()]

    def auditoria_resumo(self, f: FiltrosDashboard) -> AuditoriaResumoSchema:
        stmt = select(func.count(Pedido.id), func.coalesce(func.sum(Pedido.valor_desconto), 0.0)).where(self._flag_recuperado())
        stmt = self._aplicar_filtros_pedido(stmt, f)
        total, valor_desconto = self.session.execute(stmt).one()
        return AuditoriaResumoSchema(total_pedidos=total, valor_desconto_total=round(valor_desconto, 2))

    def auditoria_por_vendedor(self, f: FiltrosDashboard) -> list[SeriePontoSchema]:
        vendedor = func.coalesce(Pedido.vendedor, "NAO INFORMADO")
        stmt = (
            select(vendedor, func.count(Pedido.id))
            .where(self._flag_recuperado())
            .group_by(vendedor)
            .order_by(func.count(Pedido.id).desc())
            .limit(TOP_N)
        )
        stmt = self._aplicar_filtros_pedido(stmt, f)
        rows = self.session.execute(stmt).all()
        return [SeriePontoSchema(chave=nome, valor=float(qtd)) for nome, qtd in rows]

    def auditoria_pedidos(self, f: FiltrosDashboard) -> list[PedidoAuditoriaSchema]:
        stmt = select(Pedido).where(self._flag_recuperado())
        stmt = self._aplicar_filtros_pedido(stmt, f)
        stmt = stmt.order_by(Pedido.valor_desconto.desc()).limit(LIMITE_AUDITORIA)
        pedidos = self.session.execute(stmt).scalars().all()
        return [
            PedidoAuditoriaSchema(
                loja=p.loja,
                pedido=p.pedido,
                data=p.data,
                hora=p.hora,
                vendedor=p.vendedor,
                cliente=p.cliente,
                total=p.total,
                perc_desconto=p.perc_desconto,
                valor_desconto=p.valor_desconto,
                valor_liquido=p.valor_liquido,
                situacao=p.situacao,
            )
            for p in pedidos
        ]
