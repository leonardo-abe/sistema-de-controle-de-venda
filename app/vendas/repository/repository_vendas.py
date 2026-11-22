from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.vendas.models import ImportBatch, ItemVenda, Pagamento, Pedido, Produto


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

    def list_batches(self) -> list[ImportBatch]:
        stmt = select(ImportBatch).order_by(ImportBatch.data_referencia.desc(), ImportBatch.importado_em.desc())
        return list(self.session.execute(stmt).scalars().all())
