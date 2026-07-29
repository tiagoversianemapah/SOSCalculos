"""Rotas de `deducao` (paridade SOSCálculos, passo "Deduções" — só
relevante quando `Processo.configura_deducoes` é True)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.deducao import Deducao
from app.models.enums import DonoTipo
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento, JurosSegmento
from app.schemas.deducao import DeducaoCreate, DeducaoOut, DeducaoUpdate

router = APIRouter(tags=["deducoes"])

_CAMPOS_DIRETOS = (
    "tipo",
    "historico",
    "data_inicial",
    "valor",
    "atualizacao_tipo",
    "data_atualizacao",
    "fonte_criterio",
    "usa_correcao_default",
    "usa_juros_default",
)


def _obter_processo_ou_404(db: Session, processo_id: UUID) -> Processo:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")
    return processo


def _obter_deducao_ou_404(db: Session, deducao_id: UUID) -> Deducao:
    deducao = db.get(Deducao, deducao_id)
    if deducao is None:
        raise HTTPException(status_code=404, detail="dedução não encontrada")
    return deducao


def _substituir_segmentos_override(db: Session, deducao: Deducao, payload: DeducaoCreate) -> None:
    for segmento in list(deducao.correcao_segmentos_override):
        db.delete(segmento)
    for segmento in list(deducao.juros_segmentos_override):
        db.delete(segmento)
    db.flush()
    for item in payload.correcao_segmentos_override:
        db.add(
            CorrecaoSegmento(deducao_id=deducao.id, dono_tipo=DonoTipo.DEDUCAO_OVERRIDE, **item.model_dump())
        )
    for item in payload.juros_segmentos_override:
        db.add(
            JurosSegmento(deducao_id=deducao.id, dono_tipo=DonoTipo.DEDUCAO_OVERRIDE, **item.model_dump())
        )


@router.get("/processos/{processo_id}/deducoes", response_model=list[DeducaoOut])
def listar_deducoes(processo_id: UUID, db: Session = Depends(get_db)) -> list[Deducao]:
    _obter_processo_ou_404(db, processo_id)
    return db.execute(
        select(Deducao).where(Deducao.processo_id == processo_id).order_by(Deducao.data_inicial)
    ).scalars().all()


@router.post("/processos/{processo_id}/deducoes", response_model=DeducaoOut, status_code=201)
def criar_deducao(processo_id: UUID, payload: DeducaoCreate, db: Session = Depends(get_db)) -> Deducao:
    _obter_processo_ou_404(db, processo_id)
    dados = payload.model_dump(include=set(_CAMPOS_DIRETOS))
    deducao = Deducao(processo_id=processo_id, **dados)
    db.add(deducao)
    db.flush()
    _substituir_segmentos_override(db, deducao, payload)
    db.commit()
    db.refresh(deducao)
    return deducao


@router.put("/deducoes/{deducao_id}", response_model=DeducaoOut)
def atualizar_deducao(deducao_id: UUID, payload: DeducaoUpdate, db: Session = Depends(get_db)) -> Deducao:
    deducao = _obter_deducao_ou_404(db, deducao_id)
    for campo in _CAMPOS_DIRETOS:
        setattr(deducao, campo, getattr(payload, campo))
    _substituir_segmentos_override(db, deducao, payload)
    db.commit()
    db.refresh(deducao)
    return deducao


@router.delete("/deducoes/{deducao_id}", status_code=204)
def remover_deducao(deducao_id: UUID, db: Session = Depends(get_db)) -> None:
    deducao = _obter_deducao_ou_404(db, deducao_id)
    db.delete(deducao)
    db.commit()
