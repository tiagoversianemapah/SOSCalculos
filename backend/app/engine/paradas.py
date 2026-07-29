"""Resolução de paradas extraordinárias por competência (seção 3.5)."""
from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from .types import ParadaExtraordinaria


def parada_ativa_em(
    paradas: Sequence[ParadaExtraordinaria], competencia: date
) -> Optional[ParadaExtraordinaria]:
    """Retorna a primeira parada cujo intervalo cobre a competência
    informada, ou None se nenhuma parada estiver ativa nesse mês.
    """
    for parada in paradas:
        if parada.data_inicio <= competencia <= parada.data_fim:
            return parada
    return None
