import json
from collections import Counter

from fastapi import HTTPException, UploadFile, status

from app.vendas.dto.import_dto import ImportResultSchema
from app.vendas.interface.irepository_vendas import VendasRepositoryProtocol
from app.vendas.models import ImportBatch, ItemVenda, Pagamento, Pedido, PedidoPendente, Produto
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

        # As lojas desse arquivo: a substituicao e escopada por loja+dia, nao
        # pelo dia inteiro - importar a filial 2 nao pode apagar a filial 1
        # do mesmo dia.
        lojas_no_arquivo = sorted({parse_int(row.get("Loja")) for row in pedidos_rows if row.get("Pedido")})

        chaves_pendentes, pendencias = self._detectar_pendencias(pedidos_rows, pagamentos_rows, produtos_rows, data_referencia)

        pedidos_rows_ok = [r for r in pedidos_rows if self._chave(r) not in chaves_pendentes]
        pagamentos_rows_ok = [r for r in pagamentos_rows if self._chave(r) not in chaves_pendentes]

        pedidos_removidos = self.repository.delete_dados_por_lojas_e_data(
            lojas_no_arquivo, data_referencia, chaves_pendentes
        )
        substituiu = pedidos_removidos > 0

        batch = self.repository.create_batch(
            ImportBatch(
                data_referencia=data_referencia,
                lojas=",".join(str(loja) for loja in lojas_no_arquivo),
                arquivo_pedidos=arquivo_pedidos.filename or "",
                arquivo_pagamentos=arquivo_pagamentos.filename or "",
                arquivo_produtos=arquivo_produtos.filename or "",
            )
        )

        pedidos = self._montar_pedidos(pedidos_rows_ok, batch.id)
        pagamentos = self._montar_pagamentos(pagamentos_rows_ok, batch.id)
        # O catalogo de produtos e atualizado com TODAS as linhas (inclusive
        # as pendentes), ja que e so um cadastro compartilhado; os itens de
        # venda em si ficam de fora enquanto o pedido estiver pendente.
        produtos, itens_todos = self._montar_produtos_e_itens(produtos_rows, batch.id)
        itens = [item for item in itens_todos if (item.loja, item.pedido) not in chaves_pendentes]

        self.repository.bulk_insert_pedidos(pedidos)
        self.repository.upsert_produtos(produtos)
        self.repository.bulk_insert_pagamentos(pagamentos)
        self.repository.bulk_insert_itens(itens)

        for pendencia in pendencias:
            pendencia.lote_novo_id = batch.id
        self.repository.criar_pendencias(pendencias)

        batch.total_pedidos = len(pedidos)
        batch.total_pagamentos = len(pagamentos)
        batch.total_itens = len(itens)
        self.repository.update_batch_totals(batch)

        return ImportResultSchema(
            data_referencia=data_referencia,
            lojas=batch.lojas,
            total_pedidos=len(pedidos),
            total_pagamentos=len(pagamentos),
            total_itens=len(itens),
            importado_em=batch.importado_em,
            substituiu_batch_anterior=substituiu,
            total_pendencias=len(pendencias),
        )

    def resolver_pendencia(self, pendencia_id: int, usar_novo: bool) -> None:
        pendencia = self.repository.get_pendencia(pendencia_id)
        if pendencia is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pendencia nao encontrada")
        if pendencia.resolvido:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Essa pendencia ja foi resolvida")

        if usar_novo:
            self.repository.delete_pedido_exato(pendencia.loja, pendencia.pedido, pendencia.data_existente)
            pedido_row = json.loads(pendencia.pedido_row_json)
            itens_rows = json.loads(pendencia.itens_rows_json)
            pagamentos_rows = json.loads(pendencia.pagamentos_rows_json)

            pedidos = self._montar_pedidos([pedido_row], pendencia.lote_novo_id)
            pagamentos = self._montar_pagamentos(pagamentos_rows, pendencia.lote_novo_id)
            _, itens = self._montar_produtos_e_itens(itens_rows, pendencia.lote_novo_id)

            self.repository.bulk_insert_pedidos(pedidos)
            self.repository.bulk_insert_pagamentos(pagamentos)
            self.repository.bulk_insert_itens(itens)

        self.repository.marcar_pendencia_resolvida(pendencia_id, "usou_novo" if usar_novo else "manteve_antigo")

    def montar_comparacao(self, pendencia: PedidoPendente) -> dict:
        existente_pedido = self.repository.get_pedido_por_chave_e_data(
            pendencia.loja, pendencia.pedido, pendencia.data_existente
        )
        existente_itens = self.repository.list_itens(pendencia.loja, pendencia.pedido, pendencia.data_existente)
        existente_pagamentos = self.repository.list_pagamentos(
            pendencia.loja, pendencia.pedido, pendencia.data_existente
        )

        pedido_row = json.loads(pendencia.pedido_row_json)
        itens_rows = json.loads(pendencia.itens_rows_json)
        pagamentos_rows = json.loads(pendencia.pagamentos_rows_json)
        novo_pedido = self._montar_pedidos([pedido_row], 0)[0] if pedido_row else None
        novo_pagamentos = self._montar_pagamentos(pagamentos_rows, 0)
        _, novo_itens = self._montar_produtos_e_itens(itens_rows, 0)

        codigos = {i.cod_prod for i in existente_itens} | {i.cod_prod for i in novo_itens}
        produtos_por_codigo = self.repository.get_produtos_por_codigos(list(codigos))

        campos_pedido = [
            ("data", "Data"),
            ("hora", "Hora"),
            ("cliente", "Cliente"),
            ("vendedor", "Vendedor"),
            ("cidade", "Cidade"),
            ("bairro", "Bairro"),
            ("total", "Total"),
            ("perc_desconto", "% Desconto"),
            ("valor_desconto", "Valor desconto"),
            ("valor_liquido", "Valor liquido"),
            ("situacao", "Situacao"),
        ]
        diffs_pedido = [
            {
                "campo": label,
                "antigo": getattr(existente_pedido, chave) if existente_pedido else None,
                "novo": getattr(novo_pedido, chave) if novo_pedido else None,
                "diferente": (getattr(existente_pedido, chave) if existente_pedido else None)
                != (getattr(novo_pedido, chave) if novo_pedido else None),
            }
            for chave, label in campos_pedido
        ]

        def nome_produto(cod_prod: int) -> str:
            produto = produtos_por_codigo.get(cod_prod)
            return produto.nome if produto else f"PRODUTO {cod_prod}"

        itens_por_codigo: dict[int, dict] = {}
        for item in existente_itens:
            itens_por_codigo.setdefault(item.cod_prod, {})["antigo"] = item
        for item in novo_itens:
            itens_por_codigo.setdefault(item.cod_prod, {})["novo"] = item

        diffs_itens = []
        for cod_prod, versoes in sorted(itens_por_codigo.items()):
            antigo = versoes.get("antigo")
            novo = versoes.get("novo")
            diffs_itens.append(
                {
                    "cod_prod": cod_prod,
                    "produto": nome_produto(cod_prod),
                    "antigo": antigo,
                    "novo": novo,
                    "so_no_antigo": antigo is not None and novo is None,
                    "so_no_novo": novo is not None and antigo is None,
                    "diferente": antigo is not None
                    and novo is not None
                    and (antigo.quantidade != novo.quantidade or antigo.valor_total != novo.valor_total),
                }
            )

        pagamentos_por_tipo: dict[str, dict] = {}
        for pagamento in existente_pagamentos:
            pagamentos_por_tipo.setdefault(pagamento.tipo_pagamento, {})["antigo"] = pagamento
        for pagamento in novo_pagamentos:
            pagamentos_por_tipo.setdefault(pagamento.tipo_pagamento, {})["novo"] = pagamento

        diffs_pagamentos = []
        for tipo, versoes in sorted(pagamentos_por_tipo.items()):
            antigo = versoes.get("antigo")
            novo = versoes.get("novo")
            diffs_pagamentos.append(
                {
                    "tipo_pagamento": tipo,
                    "antigo": antigo,
                    "novo": novo,
                    "diferente": antigo is not None and novo is not None and antigo.valor != novo.valor,
                }
            )

        return {
            "pendencia": pendencia,
            "pedido": diffs_pedido,
            "itens": diffs_itens,
            "pagamentos": diffs_pagamentos,
        }

    @staticmethod
    def _chave(row: dict[str, str]) -> tuple[int, int]:
        return (parse_int(row.get("Loja")), parse_int(row.get("Pedido")))

    @staticmethod
    def _pedido_identico(existente: Pedido, row: dict[str, str]) -> bool:
        # Compara pedido/data/hora/vendedor/valor (os campos que o cliente
        # pediu) entre o que ja esta salvo e a linha que acabou de chegar,
        # para distinguir uma reexportacao da mesma venda (nada mudou) de
        # uma divergencia real que precisa de revisao manual.
        try:
            data_nova = parse_data(row["Data"]) if row.get("Data") else None
            hora_nova = parse_hora(row["Hora"]) if row.get("Hora") else None
        except ValueError:
            return False
        vendedor_novo = clean_str(row.get("Vendedor"))
        total_novo = parse_decimal(row.get("Total"))
        return (
            existente.data == data_nova
            and existente.hora == hora_nova
            and existente.vendedor == vendedor_novo
            and abs(existente.total - total_novo) < 0.01
        )

    def _detectar_pendencias(
        self,
        pedidos_rows: list[dict[str, str]],
        pagamentos_rows: list[dict[str, str]],
        produtos_rows: list[dict[str, str]],
        data_referencia_novo,
    ) -> tuple[set[tuple[int, int]], list[PedidoPendente]]:
        # Um pedido e unico por (loja, pedido), independente de data. Se o
        # arquivo traz um pedido que ja existe no banco numa data diferente
        # da que esta sendo importada agora (ex.: uma exportacao anterior
        # incluiu, por engano, um pedido do dia errado - ou o cliente mesmo
        # confirma que isso acontece com alguma frequencia), so vira
        # pendencia de revisao manual se o CONTEUDO tambem for diferente
        # (data, hora, vendedor, valor). Se for a mesma venda reexportada
        # sob um rotulo de dia diferente (conteudo identico), nao ha nada
        # para revisar: fica como ja estava, sem pendencia. O resto do
        # arquivo (e as reimportacoes normais do mesmo dia) seguem
        # substituindo direto, sem essa checagem extra.
        #
        # Importante: alem de comparar com a data_referencia_novo (majoritaria
        # do arquivo), tambem validamos a data PROPRIA de cada linha. Um
        # arquivo pode trazer, isolado, um pedido de um dia diferente da
        # maioria - se so olhassemos a data do arquivo, esse caso passaria
        # batido (foi exatamente isso que causou o bug original de pedido
        # gravado com o lote errado). So tratamos como "reimportacao normal
        # do mesmo dia" (sem checagem nenhuma) quando TODO MUNDO concorda
        # sobre a data: o que ja esta salvo, a data do lote e a propria
        # linha do arquivo.
        chaves: set[tuple[int, int]] = set()
        pendencias: list[PedidoPendente] = []
        vistos: set[tuple[int, int]] = set()
        for row in pedidos_rows:
            if not row.get("Pedido"):
                continue
            chave = self._chave(row)
            if chave in vistos:
                continue
            vistos.add(chave)
            loja, pedido = chave

            existente = self.repository.get_pedido_por_chave(loja, pedido)
            if existente is None:
                continue

            try:
                data_propria_linha = parse_data(row["Data"]) if row.get("Data") else None
            except ValueError:
                data_propria_linha = None

            if existente.data == data_referencia_novo and data_propria_linha == data_referencia_novo:
                # reimportacao normal do mesmo dia: nada diverge, segue o
                # fluxo normal de substituicao (apaga e recria), sem checagem.
                continue

            # Ha uma divergencia de data em algum ponto (o que ja esta salvo
            # e/ou a propria linha nao batem com a data do lote). O pedido
            # existente nao sera necessariamente apagado pela substituicao
            # escopada por data_referencia, entao precisa ficar de fora do
            # insert normal para nao duplicar - e so vira pendencia de
            # revisao manual se o CONTEUDO tambem for diferente.
            chaves.add(chave)
            if self._pedido_identico(existente, row):
                continue

            itens_rows = [r for r in produtos_rows if self._chave(r) == chave and r.get("Cod Prod")]
            pagamentos_rows_pedido = [r for r in pagamentos_rows if self._chave(r) == chave]
            pendencias.append(
                PedidoPendente(
                    loja=loja,
                    pedido=pedido,
                    data_existente=existente.data,
                    data_nova=data_propria_linha or data_referencia_novo,
                    lote_novo_id=0,
                    pedido_row_json=json.dumps(row),
                    itens_rows_json=json.dumps(itens_rows),
                    pagamentos_rows_json=json.dumps(pagamentos_rows_pedido),
                )
            )

        return chaves, pendencias

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

            quantidade = parse_decimal(row.get("Quantidade"))
            custo_unitario = parse_decimal(row.get("Custo"))
            itens.append(
                ItemVenda(
                    loja=parse_int(row.get("Loja")),
                    pedido=parse_int(row.get("Pedido")),
                    data=parse_data(row["Data"]),
                    hora=parse_hora(row["Hora"]),
                    cod_prod=cod_prod,
                    quantidade=quantidade,
                    unidade=clean_str(row.get("Unidade")),
                    valor_unitario=parse_decimal(row.get("Valor Unitario")),
                    valor_total=parse_decimal(row.get("Valor Total")),
                    # "Custo" no CSV e o custo por unidade, nao o custo total
                    # da linha (diferente de "Valor Unitario"/"Valor Total",
                    # que ja vem o par unitario/total). Convertemos aqui pra
                    # custo total da linha, consistente com valor_total.
                    custo=round(custo_unitario * quantidade, 2),
                    import_batch_id=batch_id,
                )
            )

        return list(produtos_map.values()), itens
