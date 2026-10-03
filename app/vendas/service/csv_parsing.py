import csv
import io
import re
from datetime import date, datetime, time

CSV_ENCODING = "cp1252"
CSV_DELIMITER = ";"

PEDIDOS_PATTERN = re.compile(r"^vendas_(\d{8})\.csv$", re.IGNORECASE)
PAGAMENTOS_PATTERN = re.compile(r"^vendas_(\d{8})_pagamentos\.csv$", re.IGNORECASE)
PRODUTOS_PATTERN = re.compile(r"^vendas_(\d{8})_produtos\.csv$", re.IGNORECASE)


class CsvValidationError(Exception):
    pass


def extract_data_referencia(filename: str, pattern: re.Pattern, tipo: str) -> date:
    match = pattern.match(filename.strip())
    if not match:
        raise CsvValidationError(
            f"Nome de arquivo invalido para '{tipo}': '{filename}'. "
            f"Esperado o padrao 'vendas_DDMMAAAA{'_' + tipo if tipo else ''}.csv'."
        )
    raw_date = match.group(1)
    return datetime.strptime(raw_date, "%d%m%Y").date()


def parse_decimal(value: str | None) -> float:
    if value is None:
        return 0.0
    value = value.strip()
    if not value:
        return 0.0
    normalized = value.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return 0.0


def parse_int(value: str | None) -> int:
    if value is None:
        return 0
    value = value.strip()
    if not value:
        return 0
    return int(float(value.replace(",", ".")))


def parse_data(value: str) -> date:
    return datetime.strptime(value.strip(), "%d/%m/%Y").date()


def parse_hora(value: str) -> time:
    value = value.strip()
    parts = value.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)


def read_rows(raw_bytes: bytes) -> list[dict[str, str]]:
    text = raw_bytes.decode(CSV_ENCODING)
    header_line, _, rest = text.partition("\n")
    # Alguns exports saem com uma virgula em vez de ';' separando as duas
    # ultimas colunas do cabecalho (ex.: "Valor Liquido,Situacao"); o corpo
    # do arquivo usa ';' normalmente, entao normalizamos so o cabecalho.
    header_line = header_line.replace(",", CSV_DELIMITER)
    text = header_line + "\n" + rest
    reader = csv.DictReader(io.StringIO(text), delimiter=CSV_DELIMITER)
    return [row for row in reader]


def clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None
