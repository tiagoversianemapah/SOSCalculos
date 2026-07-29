"""Fábrica de séries de índice falsas para os testes do motor de cálculo.

Não acessa banco nem rede — é o mesmo papel que `services/indices/`
cumpriria em produção (implementar `BuscarVariacao`), só que com uma
tabela fixa em memória, montada por cada teste.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Mapping, Tuple

from app.engine.types import BuscarVariacao, Indice

TabelaIndices = Mapping[Tuple[Indice, date], Decimal]


def criar_buscar_variacao(tabela: TabelaIndices) -> BuscarVariacao:
    def _buscar(indice: Indice, competencia: date) -> Decimal:
        chave = (indice, competencia)
        if chave not in tabela:
            raise KeyError(
                f"variação não cadastrada para {indice.value!r} em {competencia.isoformat()}"
            )
        return tabela[chave]

    return _buscar
