"""Resolução de segmentos de correção monetária por competência (seção 3.2)."""
from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from .types import CorrecaoSegmento


def segmento_correcao_vigente_em(
    segmentos: Sequence[CorrecaoSegmento], competencia: date
) -> Optional[CorrecaoSegmento]:
    """Localiza o segmento de correção que cobre a competência informada.

    Pressupõe que os segmentos não se sobrepõem — é responsabilidade da
    camada de serviço (que monta a lista a partir do banco) garantir
    isso. Se nenhum segmento cobrir a competência, retorna None, o que
    o motor trata como "sem correção" nesse trecho.
    """
    for segmento in segmentos:
        if segmento.data_inicio <= competencia and (
            segmento.data_fim is None or competencia <= segmento.data_fim
        ):
            return segmento
    return None
