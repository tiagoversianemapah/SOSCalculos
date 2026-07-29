from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.engine.types import Indice, TipoTaxaJuros

from .tipos import DecimalStr


class LinhaMemoriaOut(BaseModel):
    competencia: date
    saldo_inicio: DecimalStr
    indice: Optional[Indice] = None
    variacao_indice: DecimalStr
    saldo_corrigido: DecimalStr
    tipo_taxa_juros: Optional[TipoTaxaJuros] = None
    taxa_juros_mensal: DecimalStr
    juros_mes: DecimalStr
    saldo_final: DecimalStr
    parada_ativa: bool
    quitado: bool = False


class ResultadoParcelaOut(BaseModel):
    parcela_id: UUID
    valor_apurado: DecimalStr
    memoria: list[LinhaMemoriaOut]


class ResultadoAcessorioOut(BaseModel):
    acessorio_id: UUID
    valor_apurado: DecimalStr
    memoria: list[LinhaMemoriaOut]


class ResultadoDeducaoOut(BaseModel):
    deducao_id: UUID
    valor_apurado: DecimalStr
    memoria: list[LinhaMemoriaOut]


class CalculoPreviewOut(BaseModel):
    parcelas: list[ResultadoParcelaOut]
    acessorios: list[ResultadoAcessorioOut]
    deducoes: list[ResultadoDeducaoOut] = []
    total_geral: DecimalStr
