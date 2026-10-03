from datetime import date

from pydantic import BaseModel


class ClienteListItemSchema(BaseModel):
    cliente: str
    total_pedidos: int
    valor_total: float
    ticket_medio: float
    ultima_compra: date
    pedidos_sinalizados: int


class ClientePaginaSchema(BaseModel):
    itens: list[ClienteListItemSchema]
    total: int
    pagina: int
    por_pagina: int
