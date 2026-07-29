from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import TipoAtualizacaoDeducao, TipoDeducao

from .segmento import CorrecaoSegmentoIn, CorrecaoSegmentoOut, JurosSegmentoIn, JurosSegmentoOut
from .tipos import DecimalStr


class DeducaoCreate(BaseModel):
    tipo: TipoDeducao
    historico: Optional[str] = None
    data_inicial: date
    valor: DecimalStr
    atualizacao_tipo: TipoAtualizacaoDeducao = TipoAtualizacaoDeducao.DATA_INICIAL
    data_atualizacao: Optional[date] = None
    fonte_criterio: Optional[str] = None
    usa_correcao_default: bool = True
    usa_juros_default: bool = True
    correcao_segmentos_override: list[CorrecaoSegmentoIn] = []
    juros_segmentos_override: list[JurosSegmentoIn] = []

    @model_validator(mode="after")
    def _validar_data_atualizacao(self) -> "DeducaoCreate":
        if (
            self.atualizacao_tipo in (TipoAtualizacaoDeducao.OUTRA_DATA, TipoAtualizacaoDeducao.DATA_LEVANTAMENTO)
            and self.data_atualizacao is None
        ):
            raise ValueError(
                "data_atualizacao é obrigatória quando atualizacao_tipo = outra_data ou data_levantamento"
            )
        return self


class DeducaoUpdate(DeducaoCreate):
    pass


class DeducaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tipo: TipoDeducao
    historico: Optional[str] = None
    data_inicial: date
    valor: DecimalStr
    atualizacao_tipo: TipoAtualizacaoDeducao
    data_atualizacao: Optional[date] = None
    fonte_criterio: Optional[str] = None
    usa_correcao_default: bool
    usa_juros_default: bool
    correcao_segmentos_override: list[CorrecaoSegmentoOut] = []
    juros_segmentos_override: list[JurosSegmentoOut] = []
