from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ParadaCreate(BaseModel):
    data_inicio: date
    data_fim: date
    motivo: str
    suspende_correcao: bool = False
    suspende_juros: bool = False

    @model_validator(mode="after")
    def _validar_datas(self) -> "ParadaCreate":
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio")
        return self


class ParadaUpdate(ParadaCreate):
    pass


class ParadaOut(ParadaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
