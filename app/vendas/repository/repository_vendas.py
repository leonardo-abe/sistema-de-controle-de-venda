from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.vendas.models import ImportBatch, ItemVenda, Pagamento, Pedido, Produto


class RepositoryVendas:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_batch_by_data(self, data_referencia: date) -> ImportBatch | None:
        stmt = select(ImportBatch).where(ImportBatch.data_referencia == data_referencia)
        return self.session.execute(stmt).scalar_one_or_none()

    def delete_batch_data(self, batch_id: int) -> None:
        self.session.execute(delete(ItemVenda).where(ItemVenda.import_batch_id == batch_id))
        self.session.execute(delete(Pagamento).where(Pagamento.import_batch_id == batch_id))
        self.session.execute(delete(Pedido).where(Pedido.import_batch_id == batch_id))
        self.session.execute(delete(ImportBatch).where(ImportBatch.id == batch_id))
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

    def list_batches(self) -> list[ImportBatch]:
        stmt = select(ImportBatch).order_by(ImportBatch.data_referencia.desc())
        return list(self.session.execute(stmt).scalars().all())
