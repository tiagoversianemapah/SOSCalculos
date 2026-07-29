from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.engine.types import Indice
from app.models.enums import FonteIndice


class IndiceStatusOut(BaseModel):
    indice: Indice
    ultima_competencia: Optional[date] = None
    fonte: Optional[FonteIndice] = None
    ultima_atualizacao: Optional[datetime] = None


class AtualizarIndicesOut(BaseModel):
    # chave = Indice.value (ex.: "ipca"); valor = quantidade gravada ou "offline"
    resultado: dict[str, str]


class AppStatusOut(BaseModel):
    versao_local: str
    versao_publicada: Optional[str] = None
    caminho_banco: str
    online: bool
