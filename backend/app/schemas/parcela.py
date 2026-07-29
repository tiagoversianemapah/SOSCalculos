from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .pagamento import PagamentoParcialOut
from .segmento import CorrecaoSegmentoIn, CorrecaoSegmentoOut, JurosSegmentoIn, JurosSegmentoOut
from .tipos import DecimalStr


class ParcelaCreate(BaseModel):
    vencimento: date
    historico: str
    valor_bruto: DecimalStr
    usa_correcao_default: bool = True
    usa_juros_default: bool = True
    multa_percentual: Optional[DecimalStr] = None
    # Só fazem sentido (e só são persistidos) quando o respectivo
    # usa_*_default é False — seção 4, passo 2.
    correcao_segmentos_override: list[CorrecaoSegmentoIn] = []
    juros_segmentos_override: list[JurosSegmentoIn] = []


class ParcelaUpdate(ParcelaCreate):
    pass


class ParcelaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    processo_id: UUID
    vencimento: date
    historico: str
    valor_bruto: DecimalStr
    valor_apurado: Optional[DecimalStr] = None
    usa_correcao_default: bool
    usa_juros_default: bool
    multa_percentual: Optional[DecimalStr] = None
    pagamentos: list[PagamentoParcialOut] = []
    correcao_segmentos_override: list[CorrecaoSegmentoOut] = []
    juros_segmentos_override: list[JurosSegmentoOut] = []
