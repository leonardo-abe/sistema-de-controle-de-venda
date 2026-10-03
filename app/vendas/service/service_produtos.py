from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.vendas.dto.produto_dto import OpcoesProdutoSchema, ProdutoListItemSchema, ProdutoPaginaSchema
from app.vendas.models import ItemVenda, Produto

POR_PAGINA_PADRAO = 20


class ServiceProdutos:
    def __init__(self, session: Session) -> None:
        self.session = session

    def opcoes_filtro(self) -> OpcoesProdutoSchema:
        grupos = (
            self.session.execute(select(Produto.grupo).where(Produto.grupo.is_not(None)).distinct().order_by(Produto.grupo))
            .scalars()
            .all()
        )
        marcas = (
            self.session.execute(select(Produto.marca).where(Produto.marca.is_not(None)).distinct().order_by(Produto.marca))
            .scalars()
            .all()
        )
        return OpcoesProdutoSchema(grupos=list(grupos), marcas=list(marcas))

    def listar(
        self,
        busca: str | None,
        grupo: str | None,
        marca: str | None,
        pagina: int,
        por_pagina: int = POR_PAGINA_PADRAO,
    ) -> ProdutoPaginaSchema:
        base = select(Produto)
        if busca:
            base = base.where(Produto.nome.ilike(f"%{busca}%"))
        if grupo:
            base = base.where(Produto.grupo == grupo)
        if marca:
            base = base.where(Produto.marca == marca)

        total = self.session.execute(select(func.count()).select_from(base.subquery())).scalar_one()

        quantidade = func.coalesce(func.sum(ItemVenda.quantidade), 0.0)
        valor = func.coalesce(func.sum(ItemVenda.valor_total), 0.0)
        custo = func.coalesce(func.sum(ItemVenda.custo), 0.0)
        margem = func.coalesce(func.sum(ItemVenda.valor_total - ItemVenda.custo), 0.0)

        stmt = (
            select(Produto.cod_prod, Produto.nome, Produto.grupo, Produto.marca, quantidade, valor, custo, margem)
            .select_from(Produto)
            .outerjoin(ItemVenda, ItemVenda.cod_prod == Produto.cod_prod)
        )
        if busca:
            stmt = stmt.where(Produto.nome.ilike(f"%{busca}%"))
        if grupo:
            stmt = stmt.where(Produto.grupo == grupo)
        if marca:
            stmt = stmt.where(Produto.marca == marca)

        stmt = (
            stmt.group_by(Produto.cod_prod, Produto.nome, Produto.grupo, Produto.marca)
            .order_by(valor.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )

        rows = self.session.execute(stmt).all()
        itens = [
            ProdutoListItemSchema(
                cod_prod=cod_prod,
                nome=nome,
                grupo=grupo_item,
                marca=marca_item,
                quantidade_vendida=round(qtd, 2),
                valor_vendido=round(val, 2),
                custo=round(cst, 2),
                margem=round(mg, 2),
                margem_percentual=round((mg / val) * 100, 2) if val else 0.0,
            )
            for cod_prod, nome, grupo_item, marca_item, qtd, val, cst, mg in rows
        ]

        return ProdutoPaginaSchema(itens=itens, total=total, pagina=pagina, por_pagina=por_pagina)
