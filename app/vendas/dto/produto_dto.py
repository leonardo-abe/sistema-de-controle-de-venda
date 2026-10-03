from pydantic import BaseModel


class ProdutoListItemSchema(BaseModel):
    cod_prod: int
    nome: str
    grupo: str | None
    marca: str | None
    quantidade_vendida: float
    valor_vendido: float
    margem: float


class ProdutoPaginaSchema(BaseModel):
    itens: list[ProdutoListItemSchema]
    total: int
    pagina: int
    por_pagina: int


class OpcoesProdutoSchema(BaseModel):
    grupos: list[str]
    marcas: list[str]
