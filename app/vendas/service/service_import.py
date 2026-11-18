from collections import Counter

from fastapi import HTTPException, UploadFile, status

from app.vendas.dto.import_dto import ImportResultSchema
from app.vendas.interface.irepository_vendas import VendasRepositoryProtocol
from app.vendas.models import ImportBatch, ItemVenda, Pagamento, Pedido, Produto
from app.vendas.service.csv_parsing import (
    CsvValidationError,
    PAGAMENTOS_PATTERN,
    PEDIDOS_PATTERN,
    PRODUTOS_PATTERN,
    clean_str,
    extract_data_referencia,
    parse_data,
    parse_decimal,
    parse_hora,
    parse_int,
    read_rows,
)


class ServiceImport:
    def __init__(self, repository: VendasRepositoryProtocol) -> None:
        self.repository = repository

    def importar(self, arquivo_pedidos: UploadFile, arquivo_pagamentos: UploadFile, arquivo_produtos: UploadFile) -> ImportResultSchema:
        try:
            data_pedidos = extract_data_referencia(arquivo_pedidos.filename or "", PEDIDOS_PATTERN, "")
            data_pagamentos = extract_data_referencia(arquivo_pagamentos.filename or "", PAGAMENTOS_PATTERN, "pagamentos")
            data_produtos = extract_data_referencia(arquivo_produtos.filename or "", PRODUTOS_PATTERN, "produtos")
        except CsvValidationError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        if not (data_pedidos == data_pagamentos == data_produtos):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Os 3 arquivos precisam ser da mesma data. "
                    f"Pedidos={data_pedidos}, Pagamentos={data_pagamentos}, Produtos={data_produtos}."
                ),
            )

        pedidos_rows = read_rows(arquivo_pedidos.file.read())
        pagamentos_rows = read_rows(arquivo_pagamentos.file.read())
        produtos_rows = read_rows(arquivo_produtos.file.read())

        # O nome do arquivo costuma trazer a data em que ele foi GERADO, nao
        # necessariamente a data das vendas (ex.: exportado na manha seguinte).
        # Por isso a referencia real usada no sistema e a data que de fato
        # aparece nas linhas do CSV, nao a do nome do arquivo.
        datas_encontradas = Counter(parse_data(row["Data"]) for row in pedidos_rows if row.get("Data"))
        data_referencia = datas_encontradas.most_common(1)[0][0] if datas_encontradas else data_pedidos

        substituiu = False
        batch_existente = self.repository.get_batch_by_data(data_referencia)
        if batch_existente is not None:
            self.repository.delete_batch_data(batch_existente.id)
            substituiu = True

        batch = self.repository.create_batch(
            ImportBatch(
                data_referencia=data_referencia,
                arquivo_pedidos=arquivo_pedidos.filename or "",
                arquivo_pagamentos=arquivo_pagamentos.filename or "",
                arquivo_produtos=arquivo_produtos.filename or "",
            )
        )

        pedidos = self._montar_pedidos(pedidos_rows, batch.id)
        pagamentos = self._montar_pagamentos(pagamentos_rows, batch.id)
        produtos, itens = self._montar_produtos_e_itens(produtos_rows, batch.id)

        self.repository.bulk_insert_pedidos(pedidos)
        self.repository.upsert_produtos(produtos)
        self.repository.bulk_insert_pagamentos(pagamentos)
        self.repository.bulk_insert_itens(itens)

        batch.total_pedidos = len(pedidos)
        batch.total_pagamentos = len(pagamentos)
        batch.total_itens = len(itens)
        self.repository.update_batch_totals(batch)

        return ImportResultSchema(
            data_referencia=data_referencia,
            total_pedidos=len(pedidos),
            total_pagamentos=len(pagamentos),
            total_itens=len(itens),
            importado_em=batch.importado_em,
            substituiu_batch_anterior=substituiu,
        )

    @staticmethod
    def _montar_pedidos(rows: list[dict[str, str]], batch_id: int) -> list[Pedido]:
        pedidos = []
        for row in rows:
            if not row.get("Pedido"):
                continue
            pedidos.append(
                Pedido(
                    loja=parse_int(row.get("Loja")),
                    pedido=parse_int(row.get("Pedido")),
                    data=parse_data(row["Data"]),
                    hora=parse_hora(row["Hora"]),
                    cliente=clean_str(row.get("Cliente")),
                    vendedor=clean_str(row.get("Vendedor")),
                    cidade=clean_str(row.get("Cidade")),
                    bairro=clean_str(row.get("Bairro")),
                    total=parse_decimal(row.get("Total")),
                    perc_desconto=parse_decimal(row.get("%Desconto")),
                    valor_desconto=parse_decimal(row.get("Valor Desconto")),
                    valor_liquido=parse_decimal(row.get("Valor Liquido")),
                    situacao=clean_str(row.get("Situacao")),
                    import_batch_id=batch_id,
                )
            )
        return pedidos

    @staticmethod
    def _montar_pagamentos(rows: list[dict[str, str]], batch_id: int) -> list[Pagamento]:
        pagamentos = []
        for row in rows:
            if not row.get("Pedido"):
                continue
            pagamentos.append(
                Pagamento(
                    loja=parse_int(row.get("Loja")),
                    pedido=parse_int(row.get("Pedido")),
                    data=parse_data(row["Data"]),
                    hora=parse_hora(row["Hora"]),
                    tipo_pagamento=clean_str(row.get("Tipo Pagamento")) or "NAO INFORMADO",
                    valor=parse_decimal(row.get("Valor")),
                    import_batch_id=batch_id,
                )
            )
        return pagamentos

    @staticmethod
    def _montar_produtos_e_itens(rows: list[dict[str, str]], batch_id: int) -> tuple[list[Produto], list[ItemVenda]]:
        produtos_map: dict[int, Produto] = {}
        itens = []
        for row in rows:
            if not row.get("Pedido") or not row.get("Cod Prod"):
                continue

            cod_prod = parse_int(row.get("Cod Prod"))
            if cod_prod not in produtos_map:
                produtos_map[cod_prod] = Produto(
                    cod_prod=cod_prod,
                    nome=clean_str(row.get("Produto")) or f"PRODUTO {cod_prod}",
                    grupo=clean_str(row.get("Grupo")),
                    marca=clean_str(row.get("Marca")),
                    familia=clean_str(row.get("Familia")),
                    linha=clean_str(row.get("Linha")),
                    secao=clean_str(row.get("Secao")),
                )

            itens.append(
                ItemVenda(
                    loja=parse_int(row.get("Loja")),
                    pedido=parse_int(row.get("Pedido")),
                    data=parse_data(row["Data"]),
                    hora=parse_hora(row["Hora"]),
                    cod_prod=cod_prod,
                    quantidade=parse_decimal(row.get("Quantidade")),
                    unidade=clean_str(row.get("Unidade")),
                    valor_unitario=parse_decimal(row.get("Valor Unitario")),
                    valor_total=parse_decimal(row.get("Valor Total")),
                    custo=parse_decimal(row.get("Custo")),
                    import_batch_id=batch_id,
                )
            )

        return list(produtos_map.values()), itens
