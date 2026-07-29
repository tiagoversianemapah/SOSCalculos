"""Rotas de `parcela` e `pagamento_parcial` (seção 4.5, passo 2)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.enums import DonoTipo
from app.models.pagamento_parcial import PagamentoParcial
from app.models.parcela import Parcela
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento, JurosSegmento
from app.schemas.pagamento import PagamentoParcialCreate, PagamentoParcialOut
from app.schemas.parcela import ParcelaCreate, ParcelaOut, ParcelaUpdate

router = APIRouter(tags=["parcelas"])

_CAMPOS_DIRETOS = (
    "vencimento",
    "historico",
    "valor_bruto",
    "usa_correcao_default",
    "usa_juros_default",
    "multa_percentual",
)


def _obter_processo_ou_404(db: Session, processo_id: UUID) -> Processo:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")
    return processo


def _obter_parcela_ou_404(db: Session, parcela_id: UUID) -> Parcela:
    parcela = db.get(Parcela, parcela_id)
    if parcela is None:
        raise HTTPException(status_code=404, detail="parcela não encontrada")
    return parcela


def _obter_pagamento_ou_404(db: Session, pagamento_id: UUID) -> PagamentoParcial:
    pagamento = db.get(PagamentoParcial, pagamento_id)
    if pagamento is None:
        raise HTTPException(status_code=404, detail="pagamento não encontrado")
    return pagamento


def _substituir_segmentos_override(db: Session, parcela: Parcela, payload: ParcelaCreate) -> None:
    for segmento in list(parcela.correcao_segmentos_override):
        db.delete(segmento)
    for segmento in list(parcela.juros_segmentos_override):
        db.delete(segmento)
    db.flush()
    for item in payload.correcao_segmentos_override:
        db.add(
            CorrecaoSegmento(
                parcela_id=parcela.id, dono_tipo=DonoTipo.PARCELA_OVERRIDE, **item.model_dump()
            )
        )
    for item in payload.juros_segmentos_override:
        db.add(
            JurosSegmento(
                parcela_id=parcela.id, dono_tipo=DonoTipo.PARCELA_OVERRIDE, **item.model_dump()
            )
        )


@router.get("/processos/{processo_id}/parcelas", response_model=list[ParcelaOut])
def listar_parcelas(processo_id: UUID, db: Session = Depends(get_db)) -> list[Parcela]:
    _obter_processo_ou_404(db, processo_id)
    return db.execute(
        select(Parcela).where(Parcela.processo_id == processo_id).order_by(Parcela.vencimento)
    ).scalars().all()


@router.post("/processos/{processo_id}/parcelas", response_model=ParcelaOut, status_code=201)
def criar_parcela(processo_id: UUID, payload: ParcelaCreate, db: Session = Depends(get_db)) -> Parcela:
    _obter_processo_ou_404(db, processo_id)
    dados = payload.model_dump(include=set(_CAMPOS_DIRETOS))
    parcela = Parcela(processo_id=processo_id, **dados)
    db.add(parcela)
    db.flush()
    _substituir_segmentos_override(db, parcela, payload)
    db.commit()
    db.refresh(parcela)
    return parcela


@router.put("/parcelas/{parcela_id}", response_model=ParcelaOut)
def atualizar_parcela(parcela_id: UUID, payload: ParcelaUpdate, db: Session = Depends(get_db)) -> Parcela:
    parcela = _obter_parcela_ou_404(db, parcela_id)
    for campo in _CAMPOS_DIRETOS:
        setattr(parcela, campo, getattr(payload, campo))
    parcela.valor_apurado = None  # cache invalidado — precisa recalcular (seção 2)
    _substituir_segmentos_override(db, parcela, payload)
    db.commit()
    db.refresh(parcela)
    return parcela


@router.delete("/parcelas/{parcela_id}", status_code=204)
def remover_parcela(parcela_id: UUID, db: Session = Depends(get_db)) -> None:
    parcela = _obter_parcela_ou_404(db, parcela_id)
    db.delete(parcela)
    db.commit()


@router.get("/parcelas/{parcela_id}/pagamentos", response_model=list[PagamentoParcialOut])
def listar_pagamentos(parcela_id: UUID, db: Session = Depends(get_db)) -> list[PagamentoParcial]:
    _obter_parcela_ou_404(db, parcela_id)
    return db.execute(
        select(PagamentoParcial).where(PagamentoParcial.parcela_id == parcela_id).order_by(PagamentoParcial.data)
    ).scalars().all()


@router.post("/parcelas/{parcela_id}/pagamentos", response_model=PagamentoParcialOut, status_code=201)
def criar_pagamento(
    parcela_id: UUID, payload: PagamentoParcialCreate, db: Session = Depends(get_db)
) -> PagamentoParcial:
    parcela = _obter_parcela_ou_404(db, parcela_id)
    pagamento = PagamentoParcial(parcela_id=parcela_id, **payload.model_dump())
    db.add(pagamento)
    parcela.valor_apurado = None
    db.commit()
    db.refresh(pagamento)
    return pagamento


@router.put("/pagamentos/{pagamento_id}", response_model=PagamentoParcialOut)
def atualizar_pagamento(
    pagamento_id: UUID, payload: PagamentoParcialCreate, db: Session = Depends(get_db)
) -> PagamentoParcial:
    pagamento = _obter_pagamento_ou_404(db, pagamento_id)
    for campo, valor in payload.model_dump().items():
        setattr(pagamento, campo, valor)
    pagamento.parcela.valor_apurado = None
    db.commit()
    db.refresh(pagamento)
    return pagamento


@router.delete("/pagamentos/{pagamento_id}", status_code=204)
def remover_pagamento(pagamento_id: UUID, db: Session = Depends(get_db)) -> None:
    pagamento = _obter_pagamento_ou_404(db, pagamento_id)
    pagamento.parcela.valor_apurado = None
    db.delete(pagamento)
    db.commit()
