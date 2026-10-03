from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.vendas.dto.pedido_dto import (
    ItemPedidoDetalheSchema,
    PagamentoPedidoDetalheSchema,
    PedidoDetalheSchema,
    PedidoListItemSchema,
    PedidoPaginaSchema,
)
from app.vendas.models import ItemVenda, Pagamento, Pedido, Produto
from app.vendas.service.auditoria import flag_recuperado, pedido_sinalizado

POR_PAGINA_PADRAO = 20


class ServicePedidos:
    def __init__(self, session: Session) -> None:
        self.session = session

    def listar(
        self,
        data_inicio: date | None,
        data_fim: date | None,
        vendedor: str | None,
        forma_pagamento: str | None,
        busca: str | None,
        apenas_sinalizados: bool,
        pagina: int,
        por_pagina: int = POR_PAGINA_PADRAO,
    ) -> PedidoPaginaSchema:
        condicoes = []
        if data_inicio is not None:
            condicoes.append(Pedido.data >= data_inicio)
        if data_fim is not None:
            condicoes.append(Pedido.data <= data_fim)
        if vendedor:
            condicoes.append(Pedido.vendedor == vendedor)
        if forma_pagamento:
            condicoes.append(
                select(Pagamento.id)
                .where(Pagamento.loja == Pedido.loja, Pagamento.pedido == Pedido.pedido, Pagamento.tipo_pagamento == forma_pagamento)
                .exists()
            )
        if busca:
            busca_num = busca.strip()
            if busca_num.isdigit():
                condicoes.append((Pedido.pedido == int(busca_num)) | (Pedido.cliente.ilike(f"%{busca}%")))
            else:
                condicoes.append(Pedido.cliente.ilike(f"%{busca}%"))
        if apenas_sinalizados:
            condicoes.append(flag_recuperado())

        base = select(Pedido)
        for condicao in condicoes:
            base = base.where(condicao)

        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        stmt = base.order_by(Pedido.data.desc(), Pedido.hora.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina)
        pedidos = self.session.execute(stmt).scalars().all()

        itens = [
            PedidoListItemSchema(
                loja=p.loja,
                pedido=p.pedido,
                data=p.data,
                hora=p.hora,
                cliente=p.cliente,
                vendedor=p.vendedor,
                total=p.total,
                perc_desconto=p.perc_desconto,
                valor_desconto=p.valor_desconto,
                valor_liquido=p.valor_liquido,
                situacao=p.situacao,
                sinalizado=pedido_sinalizado(p.situacao, p.perc_desconto),
            )
            for p in pedidos
        ]

        return PedidoPaginaSchema(itens=itens, total=total, pagina=pagina, por_pagina=por_pagina)

    def detalhe(self, loja: int, pedido: int) -> PedidoDetalheSchema:
        pedido_obj = self.session.execute(select(Pedido).where(Pedido.loja == loja, Pedido.pedido == pedido)).scalar_one_or_none()
        if pedido_obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido nao encontrado")

        itens_stmt = (
            select(ItemVenda, Produto)
            .join(Produto, Produto.cod_prod == ItemVenda.cod_prod)
            .where(ItemVenda.loja == loja, ItemVenda.pedido == pedido)
        )
        itens = [
            ItemPedidoDetalheSchema(
                cod_prod=item.cod_prod,
                produto=produto.nome,
                grupo=produto.grupo,
                marca=produto.marca,
                quantidade=item.quantidade,
                unidade=item.unidade,
                valor_unitario=item.valor_unitario,
                valor_total=item.valor_total,
                custo=item.custo,
                margem=round(item.valor_total - item.custo, 2),
            )
            for item, produto in self.session.execute(itens_stmt).all()
        ]

        pagamentos_stmt = select(Pagamento).where(Pagamento.loja == loja, Pagamento.pedido == pedido)
        pagamentos = [
            PagamentoPedidoDetalheSchema(tipo_pagamento=p.tipo_pagamento, valor=p.valor)
            for p in self.session.execute(pagamentos_stmt).scalars().all()
        ]

        return PedidoDetalheSchema(
            loja=pedido_obj.loja,
            pedido=pedido_obj.pedido,
            data=pedido_obj.data,
            hora=pedido_obj.hora,
            cliente=pedido_obj.cliente,
            vendedor=pedido_obj.vendedor,
            cidade=pedido_obj.cidade,
            bairro=pedido_obj.bairro,
            total=pedido_obj.total,
            perc_desconto=pedido_obj.perc_desconto,
            valor_desconto=pedido_obj.valor_desconto,
            valor_liquido=pedido_obj.valor_liquido,
            situacao=pedido_obj.situacao,
            sinalizado=pedido_sinalizado(pedido_obj.situacao, pedido_obj.perc_desconto),
            itens=itens,
            pagamentos=pagamentos,
        )
