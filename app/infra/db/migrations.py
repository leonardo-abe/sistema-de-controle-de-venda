from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def migrar_import_batches_multi_loja(engine: Engine) -> None:
    # import_batches tinha "data_referencia" UNIQUE (1 lote por dia). Para
    # suportar uma filial por arquivo no mesmo dia, isso precisa virar
    # "1 lote por loja+dia", e a tabela ganha uma coluna "lojas". SQLite nao
    # altera uma UNIQUE existente com ALTER TABLE, entao reconstruimos a
    # tabela preservando os dados (sem FK envolvida, e uma tabela isolada).
    # Seguro rodar mais de uma vez: se a tabela ainda nao existe (deploy
    # novo) ou ja tem a coluna "lojas", nao faz nada.
    if not inspect(engine).has_table("import_batches"):
        return

    colunas_atuais = {c["name"] for c in inspect(engine).get_columns("import_batches")}
    if "lojas" in colunas_atuais:
        return

    from app.vendas.models import ImportBatch

    with engine.begin() as conn:
        conn.exec_driver_sql('ALTER TABLE "import_batches" RENAME TO "import_batches_backup"')
        # Renomear a tabela nao renomeia os indices dela; apaga os indices
        # antigos para a nova tabela poder recriar os seus com o mesmo nome.
        indices_antigos = inspect(conn).get_indexes("import_batches_backup")
        for indice in indices_antigos:
            conn.exec_driver_sql(f'DROP INDEX IF EXISTS "{indice["name"]}"')
        ImportBatch.__table__.create(conn)
        conn.exec_driver_sql(
            'INSERT INTO "import_batches" '
            "(id, data_referencia, lojas, arquivo_pedidos, arquivo_pagamentos, arquivo_produtos, "
            "total_pedidos, total_pagamentos, total_itens, importado_em) "
            "SELECT id, data_referencia, '1', arquivo_pedidos, arquivo_pagamentos, arquivo_produtos, "
            "total_pedidos, total_pagamentos, total_itens, importado_em "
            'FROM "import_batches_backup"'
        )
        conn.exec_driver_sql('DROP TABLE "import_batches_backup"')
