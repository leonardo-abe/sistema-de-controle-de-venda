from datetime import date, time

from pydantic import BaseModel


class FiltroPeriodo(BaseModel):
    data_inicio: date | None = None
    data_fim: date | None = None


class KpiResumoSchema(BaseModel):
    total_pedidos: int
    valor_total_liquido: float
    ticket_medio: float
    total_desconto: float
    total_itens_vendidos: float
    margem_bruta: float


class SeriePontoSchema(BaseModel):
    chave: str
    valor: float


class SerieDuplaSchema(BaseModel):
    chave: str
    valor: float
    valor_secundario: float = 0


class AuditoriaResumoSchema(BaseModel):
    total_pedidos: int
    valor_desconto_total: float


class PedidoAuditoriaSchema(BaseModel):
    loja: int
    pedido: int
    data: date
    hora: time
    vendedor: str | None
    cliente: str | None
    total: float
    perc_desconto: float
    valor_desconto: float
    valor_liquido: float
    situacao: str | None
