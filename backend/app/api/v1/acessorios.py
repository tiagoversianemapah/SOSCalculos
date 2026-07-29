"""Rotas de `acessorio` (seção 4.5, passo 3)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.acessorio import Acessorio
from app.models.enums import DonoTipo
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento, JurosSegmento
from app.schemas.acessorio import AcessorioCreate, AcessorioOut, AcessorioUpdate

router = APIRouter(tags=["acessorios"])

_CAMPOS_DIRETOS = (
    "tipo",
    "historico",
    "percentual",
    "valor_fixo",
    "base_calculo",
    "data_evento",
    "fonte_criterio",
    "valor_diario",
    "data_inicio_acumulo",
    "usa_correcao_default",
    "usa_juros_default",
)


def _obter_processo_ou_404(db: Session, processo_id: UUID) -> Processo:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")
    return processo


def _obter_acessorio_ou_404(db: Session, acessorio_id: UUID) -> Acessorio:
    acessorio = db.get(Acessorio, acessorio_id)
    if acessorio is None:
        raise HTTPException(status_code=404, detail="acessório não encontrado")
    return acessorio


@router.get("/processos/{processo_id}/acessorios", response_model=list[AcessorioOut])
def listar_acessorios(processo_id: UUID, db: Session = Depends(get_db)) -> list[Acessorio]:
    _obter_processo_ou_404(db, processo_id)
    return db.execute(
        select(Acessorio).where(Acessorio.processo_id == processo_id)
    ).scalars().all()


def _substituir_segmentos_override(db: Session, acessorio: Acessorio, payload: AcessorioCreate) -> None:
    for segmento in list(acessorio.correcao_segmentos_override):
        db.delete(segmento)
    for segmento in list(acessorio.juros_segmentos_override):
        db.delete(segmento)
    db.flush()
    for item in payload.correcao_segmentos_override:
        db.add(
            CorrecaoSegmento(
                acessorio_id=acessorio.id, dono_tipo=DonoTipo.ACESSORIO_OVERRIDE, **item.model_dump()
            )
        )
    for item in payload.juros_segmentos_override:
        db.add(
            JurosSegmento(
                acessorio_id=acessorio.id, dono_tipo=DonoTipo.ACESSORIO_OVERRIDE, **item.model_dump()
            )
        )


@router.post("/processos/{processo_id}/acessorios", response_model=AcessorioOut, status_code=201)
def criar_acessorio(processo_id: UUID, payload: AcessorioCreate, db: Session = Depends(get_db)) -> Acessorio:
    _obter_processo_ou_404(db, processo_id)
    dados = payload.model_dump(include=set(_CAMPOS_DIRETOS))
    acessorio = Acessorio(processo_id=processo_id, **dados)
    db.add(acessorio)
    db.flush()
    _substituir_segmentos_override(db, acessorio, payload)
    db.commit()
    db.refresh(acessorio)
    return acessorio


@router.put("/acessorios/{acessorio_id}", response_model=AcessorioOut)
def atualizar_acessorio(
    acessorio_id: UUID, payload: AcessorioUpdate, db: Session = Depends(get_db)
) -> Acessorio:
    acessorio = _obter_acessorio_ou_404(db, acessorio_id)
    for campo in _CAMPOS_DIRETOS:
        setattr(acessorio, campo, getattr(payload, campo))
    _substituir_segmentos_override(db, acessorio, payload)
    db.commit()
    db.refresh(acessorio)
    return acessorio


@router.delete("/acessorios/{acessorio_id}", status_code=204)
def remover_acessorio(acessorio_id: UUID, db: Session = Depends(get_db)) -> None:
    acessorio = _obter_acessorio_ou_404(db, acessorio_id)
    db.delete(acessorio)
    db.commit()
