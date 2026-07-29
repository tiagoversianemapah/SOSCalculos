"""Resolução de segmentos de juros moratórios por competência (seção 3.3)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Sequence

from .types import BuscarVariacao, Indice, JurosSegmento, TipoTaxaJuros


def segmento_juros_vigente_em(
    segmentos: Sequence[JurosSegmento], competencia: date
) -> Optional[JurosSegmento]:
    for segmento in segmentos:
        if segmento.data_inicio <= competencia and (
            segmento.data_fim is None or competencia <= segmento.data_fim
        ):
            return segmento
    return None


def resolver_taxa_mensal(
    segmento: JurosSegmento,
    competencia: date,
    buscar_variacao: BuscarVariacao,
) -> Decimal:
    """Resolve a taxa mensal efetiva de um segmento de juros.

    PERCENTUAL_FIXO_MENSAL usa o valor configurado diretamente.
    TAXA_LEGAL busca a Selic do mês como taxa de referência — ver seção 11
    da especificação: essa é uma regra que muda conforme a legislação
    vigente na época do cálculo; não tratar como verdade fixa sem
    confirmação jurídica.

    SELIC_SUBSTITUTIVA não passa por aqui — é tratada como caso especial
    diretamente em timeline.py, porque substitui a correção monetária ao
    mesmo tempo (seção 3.4), não é só uma taxa de juros comum.
    """
    if segmento.tipo_taxa is TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL:
        assert segmento.taxa_valor is not None
        return segmento.taxa_valor
    if segmento.tipo_taxa is TipoTaxaJuros.TAXA_LEGAL:
        return buscar_variacao(Indice.SELIC_SIMPLES, competencia)
    raise ValueError(
        f"resolver_taxa_mensal não se aplica a {segmento.tipo_taxa!r} — "
        "SELIC_SUBSTITUTIVA é tratada separadamente em timeline.py"
    )
