from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .segmento import CorrecaoSegmentoIn, JurosSegmentoIn
from .tipos import DecimalStr


class SalarioMinimoValorCreate(BaseModel):
    competencia: date
    valor: DecimalStr


class SalarioMinimoValorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    competencia: date
    valor: DecimalStr


class GerarPorSalarioMinimoRequest(BaseModel):
    """Payload do botão "Salário Mínimo" do passo 2 — mesmo formato do
    "Preenchimento em Série", mas o valor de cada linha vem de
    `percentual_salario * valor_vigente_na_competencia` em vez de um
    valor fixo digitado."""

    data_inicial: date
    data_final: date
    percentual_salario: DecimalStr
    percentual_pago: Optional[DecimalStr] = None
    fim_mes: bool = False
    historico: str
    usa_correcao_default: bool = True
    usa_juros_default: bool = True
    correcao_segmentos_override: list[CorrecaoSegmentoIn] = []
    juros_segmentos_override: list[JurosSegmentoIn] = []
    multa_percentual: Optional[DecimalStr] = None
