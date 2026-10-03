from app.vendas.models import Pedido

DESCONTO_ALTO_PCT = 50.0


def flag_recuperado():
    situacao_preenchida = Pedido.situacao.is_not(None) & (Pedido.situacao != "")
    return situacao_preenchida | (Pedido.perc_desconto >= DESCONTO_ALTO_PCT)


def pedido_sinalizado(situacao: str | None, perc_desconto: float) -> bool:
    return bool(situacao and situacao.strip()) or perc_desconto >= DESCONTO_ALTO_PCT
