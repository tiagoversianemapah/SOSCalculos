"""Rotas de `parada_extraordinaria` a nível de processo (seção 4.5,
passo 3). Paradas específicas de uma parcela existem no modelo (seção 2)
mas não têm rota própria ainda — não implementado antecipadamente
(seção 12.3), só quando o produto pedir."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.parada import ParadaExtraordinaria
from app.models.processo import Processo
from app.schemas.parada import ParadaCreate, ParadaOut, ParadaUpdate

router = APIRouter(tags=["paradas"])


def _obter_processo_ou_404(db: Session, processo_id: UUID) -> Processo:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")
    return processo


def _obter_parada_ou_404(db: Session, parada_id: UUID) -> ParadaExtraordinaria:
    parada = db.get(ParadaExtraordinaria, parada_id)
    if parada is None:
        raise HTTPException(status_code=404, detail="parada não encontrada")
    return parada


@router.get("/processos/{processo_id}/paradas", response_model=list[ParadaOut])
def listar_paradas(processo_id: UUID, db: Session = Depends(get_db)) -> list[ParadaExtraordinaria]:
    _obter_processo_ou_404(db, processo_id)
    return db.execute(
        select(ParadaExtraordinaria).where(ParadaExtraordinaria.processo_id == processo_id)
    ).scalars().all()


@router.post("/processos/{processo_id}/paradas", response_model=ParadaOut, status_code=201)
def criar_parada(processo_id: UUID, payload: ParadaCreate, db: Session = Depends(get_db)) -> ParadaExtraordinaria:
    _obter_processo_ou_404(db, processo_id)
    parada = ParadaExtraordinaria(processo_id=processo_id, **payload.model_dump())
    db.add(parada)
    db.commit()
    db.refresh(parada)
    return parada


@router.put("/paradas/{parada_id}", response_model=ParadaOut)
def atualizar_parada(parada_id: UUID, payload: ParadaUpdate, db: Session = Depends(get_db)) -> ParadaExtraordinaria:
    parada = _obter_parada_ou_404(db, parada_id)
    for campo, valor in payload.model_dump().items():
        setattr(parada, campo, valor)
    db.commit()
    db.refresh(parada)
    return parada


@router.delete("/paradas/{parada_id}", status_code=204)
def remover_parada(parada_id: UUID, db: Session = Depends(get_db)) -> None:
    parada = _obter_parada_ou_404(db, parada_id)
    db.delete(parada)
    db.commit()
