"""TypeDecorator `DecimalText` — precisão exata em SQLite (seção 1/6.1/12.1).

SQLite não tem tipo decimal exato: uma coluna `Numeric` do SQLAlchemy cai
para armazenamento em float por padrão, o que violaria o requisito
central do projeto (Decimal, nunca float, em toda a cadeia). Este tipo
grava o `Decimal` como TEXT canônico (sem notação científica) no SQLite
e reconverte para `Decimal` na leitura, sem perda de dígitos —
inclusive zeros à direita.

Dialect-aware (invariante 12.1.5): em PostgreSQL usa `NUMERIC` nativo em
vez de TEXT, para que uma futura migração desktop → servidor (seção
12.2) não exija tocar nos modelos.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.types import TypeDecorator


class DecimalText(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, precision: int | None = None, scale: int | None = None, **kwargs) -> None:
        self.precision = precision
        self.scale = scale
        super().__init__(**kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Numeric(self.precision, self.scale))
        return dialect.type_descriptor(String())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError(
                "DecimalText não aceita float (perde precisão) — use Decimal ou str"
            )
        if not isinstance(value, Decimal):
            value = Decimal(value)
        if dialect.name == "postgresql":
            return value
        return format(value, "f")  # notação fixa, nunca científica (ex.: "1234.5600")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(value)
