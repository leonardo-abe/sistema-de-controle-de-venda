from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.vendas.models import ImportBatch, ItemVenda, Pagamento, Pedido, PedidoPendente, Produto


class RepositoryVendas:
    def __init__(self, session: Session) -> None:
        self.session = session

    def delete_batch_data(self, batch_id: int) -> None:
        self.session.execute(delete(ItemVenda).where(ItemVenda.import_batch_id == batch_id))
        self.session.execute(delete(Pagamento).where(Pagamento.import_batch_id == batch_id))
        self.session.execute(delete(Pedido).where(Pedido.import_batch_id == batch_id))
        self.session.execute(delete(ImportBatch).where(ImportBatch.id == batch_id))
        self.session.commit()

    def delete_dados_por_lojas_e_data(self, lojas: list[int], data_referencia: date) -> int:
        # Substitui dados existentes dessas lojas, nessa data, antes de uma
        # reimportacao - escopado por loja (nao pelo dia inteiro), para que
        # reimportar a filial 2 nao apague a filial 1 do mesmo dia.
        if not lojas:
            return 0
        pedidos_afetados = self.session.execute(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.loja.in_(lojas), Pedido.data == data_referencia)
        ).scalar_one()
        self.session.execute(
            delete(ItemVenda).where(ItemVenda.loja.in_(lojas), ItemVenda.data == data_referencia)
        )
        self.session.execute(
            delete(Pagamento).where(Pagamento.loja.in_(lojas), Pagamento.data == data_referencia)
        )
        self.session.execute(delete(Pedido).where(Pedido.loja.in_(lojas), Pedido.data == data_referencia))
        self.session.commit()
        return pedidos_afetados

    def get_pedido_por_chave(self, loja: int, pedido: int) -> Pedido | None:
        stmt = select(Pedido).where(Pedido.loja == loja, Pedido.pedido == pedido)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_pedido_por_chave_e_data(self, loja: int, pedido: int, data_referencia: date) -> Pedido | None:
        stmt = select(Pedido).where(Pedido.loja == loja, Pedido.pedido == pedido, Pedido.data == data_referencia)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_itens(self, loja: int, pedido: int, data_referencia: date) -> list[ItemVenda]:
        stmt = select(ItemVenda).where(
            ItemVenda.loja == loja, ItemVenda.pedido == pedido, ItemVenda.data == data_referencia
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_pagamentos(self, loja: int, pedido: int, data_referencia: date) -> list[Pagamento]:
        stmt = select(Pagamento).where(
            Pagamento.loja == loja, Pagamento.pedido == pedido, Pagamento.data == data_referencia
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_produtos_por_codigos(self, codigos: list[int]) -> dict[int, Produto]:
        if not codigos:
            return {}
        stmt = select(Produto).where(Produto.cod_prod.in_(codigos))
        return {p.cod_prod: p for p in self.session.execute(stmt).scalars().all()}

    def delete_pedido_exato(self, loja: int, pedido: int, data_referencia: date) -> None:
        self.session.execute(
            delete(ItemVenda).where(ItemVenda.loja == loja, ItemVenda.pedido == pedido, ItemVenda.data == data_referencia)
        )
        self.session.execute(
            delete(Pagamento).where(Pagamento.loja == loja, Pagamento.pedido == pedido, Pagamento.data == data_referencia)
        )
        self.session.execute(
            delete(Pedido).where(Pedido.loja == loja, Pedido.pedido == pedido, Pedido.data == data_referencia)
        )
        self.session.commit()

    def criar_pendencias(self, pendencias: list[PedidoPendente]) -> None:
        if not pendencias:
            return
        self.session.add_all(pendencias)
        self.session.commit()

    def list_pendencias_nao_resolvidas(self, loja: int | None = None) -> list[PedidoPendente]:
        stmt = (
            select(PedidoPendente)
            .where(PedidoPendente.resolvido.is_(False))
            .order_by(PedidoPendente.criado_em.desc())
        )
        if loja is not None:
            stmt = stmt.where(PedidoPendente.loja == loja)
        return list(self.session.execute(stmt).scalars().all())

    def get_pendencia(self, pendencia_id: int) -> PedidoPendente | None:
        stmt = select(PedidoPendente).where(PedidoPendente.id == pendencia_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def marcar_pendencia_resolvida(self, pendencia_id: int, resolucao: str) -> None:
        pendencia = self.get_pendencia(pendencia_id)
        if pendencia is None:
            return
        pendencia.resolvido = True
        pendencia.resolvido_em = datetime.now()
        pendencia.resolucao = resolucao
        self.session.commit()

    def create_batch(self, batch: ImportBatch) -> ImportBatch:
        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)
        return batch

    def update_batch_totals(self, batch: ImportBatch) -> None:
        self.session.commit()

    def bulk_insert_pedidos(self, pedidos: list[Pedido]) -> None:
        if not pedidos:
            return
        self.session.bulk_save_objects(pedidos)
        self.session.commit()

    def bulk_insert_pagamentos(self, pagamentos: list[Pagamento]) -> None:
        if not pagamentos:
            return
        self.session.bulk_save_objects(pagamentos)
        self.session.commit()

    def bulk_insert_itens(self, itens: list[ItemVenda]) -> None:
        if not itens:
            return
        self.session.bulk_save_objects(itens)
        self.session.commit()

    def upsert_produtos(self, produtos: list[Produto]) -> None:
        if not produtos:
            return
        for produto in produtos:
            stmt = sqlite_insert(Produto).values(
                cod_prod=produto.cod_prod,
                nome=produto.nome,
                grupo=produto.grupo,
                marca=produto.marca,
                familia=produto.familia,
                linha=produto.linha,
                secao=produto.secao,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["cod_prod"],
                set_={
                    "nome": stmt.excluded.nome,
                    "grupo": stmt.excluded.grupo,
                    "marca": stmt.excluded.marca,
                    "familia": stmt.excluded.familia,
                    "linha": stmt.excluded.linha,
                    "secao": stmt.excluded.secao,
                },
            )
            self.session.execute(stmt)
        self.session.commit()

    def list_batches(
        self,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        loja: int | None = None,
    ) -> list[ImportBatch]:
        stmt = select(ImportBatch).order_by(ImportBatch.data_referencia.desc(), ImportBatch.importado_em.desc())
        if data_inicio is not None:
            stmt = stmt.where(ImportBatch.data_referencia >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(ImportBatch.data_referencia <= data_fim)
        batches = list(self.session.execute(stmt).scalars().all())
        if loja is not None:
            batches = [b for b in batches if str(loja) in b.lojas.split(",")]
        return batches

    def list_lojas_distintas(self) -> list[int]:
        stmt = select(Pedido.loja).distinct().order_by(Pedido.loja)
        return list(self.session.execute(stmt).scalars().all())
