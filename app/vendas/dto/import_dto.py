from datetime import date, datetime

from pydantic import BaseModel


class ImportResultSchema(BaseModel):
    data_referencia: date
    total_pedidos: int
    total_pagamentos: int
    total_itens: int
    importado_em: datetime
    substituiu_batch_anterior: bool


class ImportBatchSchema(BaseModel):
    id: int
    data_referencia: date
    total_pedidos: int
    total_pagamentos: int
    total_itens: int
    importado_em: datetime

    model_config = {"from_attributes": True}
