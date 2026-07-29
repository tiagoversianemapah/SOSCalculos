from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import TipoPagamentoParcial

from .tipos import DecimalStr


class PagamentoParcialCreate(BaseModel):
    data: date
    valor: DecimalStr
    tipo: TipoPagamentoParcial
    descricao: Optional[str] = None
    fonte_criterio: Optional[str] = None


class PagamentoParcialOut(PagamentoParcialCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
