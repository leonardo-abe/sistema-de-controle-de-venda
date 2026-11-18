from datetime import date as date_type
from datetime import datetime, time

from sqlalchemy import Date, DateTime, ForeignKeyConstraint, String, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.sqlite import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_referencia: Mapped[date_type] = mapped_column(Date, unique=True, index=True)
    arquivo_pedidos: Mapped[str] = mapped_column(String(255))
    arquivo_pagamentos: Mapped[str] = mapped_column(String(255))
    arquivo_produtos: Mapped[str] = mapped_column(String(255))
    total_pedidos: Mapped[int] = mapped_column(default=0)
    total_pagamentos: Mapped[int] = mapped_column(default=0)
    total_itens: Mapped[int] = mapped_column(default=0)
    importado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (UniqueConstraint("loja", "pedido", name="uq_pedido_loja_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    loja: Mapped[int]
    pedido: Mapped[int] = mapped_column(index=True)
    data: Mapped[date_type] = mapped_column(Date, index=True)
    hora: Mapped[time]
    cliente: Mapped[str | None] = mapped_column(String(200))
    vendedor: Mapped[str | None] = mapped_column(String(120), index=True)
    cidade: Mapped[str | None] = mapped_column(String(120))
    bairro: Mapped[str | None] = mapped_column(String(120))
    total: Mapped[float] = mapped_column(default=0)
    perc_desconto: Mapped[float] = mapped_column(default=0)
    valor_desconto: Mapped[float] = mapped_column(default=0)
    valor_liquido: Mapped[float] = mapped_column(default=0)
    situacao: Mapped[str | None] = mapped_column(String(50))
    import_batch_id: Mapped[int] = mapped_column(index=True)


class Pagamento(Base):
    __tablename__ = "pagamentos"
    __table_args__ = (
        ForeignKeyConstraint(["loja", "pedido"], ["pedidos.loja", "pedidos.pedido"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    loja: Mapped[int]
    pedido: Mapped[int] = mapped_column(index=True)
    data: Mapped[date_type] = mapped_column(Date, index=True)
    hora: Mapped[time]
    tipo_pagamento: Mapped[str] = mapped_column(String(50), index=True)
    valor: Mapped[float] = mapped_column(default=0)
    import_batch_id: Mapped[int] = mapped_column(index=True)


class Produto(Base):
    __tablename__ = "produtos"

    cod_prod: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    grupo: Mapped[str | None] = mapped_column(String(120), index=True)
    marca: Mapped[str | None] = mapped_column(String(120), index=True)
    familia: Mapped[str | None] = mapped_column(String(120))
    linha: Mapped[str | None] = mapped_column(String(120))
    secao: Mapped[str | None] = mapped_column(String(120))


class ItemVenda(Base):
    __tablename__ = "itens_venda"
    __table_args__ = (
        ForeignKeyConstraint(["loja", "pedido"], ["pedidos.loja", "pedidos.pedido"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    loja: Mapped[int]
    pedido: Mapped[int] = mapped_column(index=True)
    data: Mapped[date_type] = mapped_column(Date, index=True)
    hora: Mapped[time]
    cod_prod: Mapped[int] = mapped_column(index=True)
    quantidade: Mapped[float] = mapped_column(default=0)
    unidade: Mapped[str | None] = mapped_column(String(20))
    valor_unitario: Mapped[float] = mapped_column(default=0)
    valor_total: Mapped[float] = mapped_column(default=0)
    custo: Mapped[float] = mapped_column(default=0)
    import_batch_id: Mapped[int] = mapped_column(index=True)
