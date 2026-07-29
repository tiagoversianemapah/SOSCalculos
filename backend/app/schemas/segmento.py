from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.engine.types import Indice, TipoTaxaJuros
from app.models.enums import TipoVencimento

from .tipos import DecimalStr


class CorrecaoSegmentoIn(BaseModel):
    ordem: int
    indice: Indice
    tribunal_codigo: Optional[str] = None
    data_inicio: date
    data_fim: Optional[date] = None
    fonte_criterio: Optional[str] = None
    vencimento_tipo: TipoVencimento = TipoVencimento.DO_VENCIMENTO
    permite_deflacao: bool = True
    compor_com_selic: bool = False


class CorrecaoSegmentoOut(CorrecaoSegmentoIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class JurosSegmentoIn(BaseModel):
    ordem: int
    tipo_taxa: TipoTaxaJuros
    taxa_valor: Optional[DecimalStr] = None
    data_inicio: date
    data_fim: Optional[date] = None
    fonte_criterio: Optional[str] = None
    vencimento_tipo: TipoVencimento = TipoVencimento.DO_VENCIMENTO


class JurosSegmentoOut(JurosSegmentoIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
