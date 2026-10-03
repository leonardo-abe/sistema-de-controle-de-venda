from datetime import date, time

from pydantic import BaseModel


class PedidoListItemSchema(BaseModel):
    loja: int
    pedido: int
    data: date
    hora: time
    cliente: str | None
    vendedor: str | None
    total: float
    perc_desconto: float
    valor_desconto: float
    valor_liquido: float
    situacao: str | None
    sinalizado: bool


class PedidoPaginaSchema(BaseModel):
    itens: list[PedidoListItemSchema]
    total: int
    pagina: int
    por_pagina: int


class ItemPedidoDetalheSchema(BaseModel):
    cod_prod: int
    produto: str
    grupo: str | None
    marca: str | None
    quantidade: float
    unidade: str | None
    valor_unitario: float
    valor_total: float
    custo: float
    margem: float


class PagamentoPedidoDetalheSchema(BaseModel):
    tipo_pagamento: str
    valor: float


class PedidoDetalheSchema(BaseModel):
    loja: int
    pedido: int
    data: date
    hora: time
    cliente: str | None
    vendedor: str | None
    cidade: str | None
    bairro: str | None
    total: float
    perc_desconto: float
    valor_desconto: float
    valor_liquido: float
    situacao: str | None
    sinalizado: bool
    itens: list[ItemPedidoDetalheSchema]
    pagamentos: list[PagamentoPedidoDetalheSchema]
