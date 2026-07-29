"""Tipo compartilhado para valores monetários/percentuais nos schemas.

Princípio de arquitetura inegociável (seção 1): valores monetários
trafegam na API como **string**, nunca como número JSON solto. Este tipo
aceita `str`/`Decimal` na entrada, rejeita `float` explicitamente, e
serializa sempre como string na saída.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer


def _validar_decimal(valor: object) -> Decimal:
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, float):
        raise ValueError(
            "valores monetários/percentuais devem ser enviados como string, nunca como float"
        )
    try:
        return Decimal(str(valor))
    except InvalidOperation as exc:
        raise ValueError(f"'{valor}' não é um valor decimal válido") from exc


DecimalStr = Annotated[
    Decimal,
    BeforeValidator(_validar_decimal),
    PlainSerializer(lambda v: str(v), return_type=str),
]
