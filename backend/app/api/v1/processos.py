"""Rotas de `processo` (seção 4.5, passo 1). Endpoints só resolvem
dados e delegam — nenhuma regra de negócio aqui (invariante 12.1.7)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.calculo_execucao import CalculoExecucao
from app.models.enums import DonoTipo
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento, JurosSegmento
from app.schemas.processo import ProcessoCreate, ProcessoListItem, ProcessoOut, ProcessoUpdate

router = APIRouter(prefix="/processos", tags=["processos"])

_CAMPOS_DIRETOS = (
    "numero_processo", "requerente", "requerido", "comarca", "vara", "data_calculo",
    "titulo_calculo", "requerente_doc", "requerido_doc", "tribunal", "tipo_acao", "observacoes",
    "contrato", "feito", "exibir_relatorio_detalhado", "exibir_relatorio_correcao", "contagem_juros",
    "configura_deducoes", "aplicar_art_354_cc",
    "data_citacao", "data_distribuicao", "data_sentenca", "data_transito_julgado", "data_publicacao",
    "data_fixa", "data_homologacao", "data_aposentadoria", "data_evento_padrao", "valor_causa",
)


def _obter_processo_ou_404(db: Session, processo_id: UUID) -> Processo:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")
    return processo


def _substituir_segmentos_default(db: Session, processo: Processo, payload: ProcessoCreate) -> None:
    for segmento in list(processo.correcao_segmentos_default):
        db.delete(segmento)
    for segmento in list(processo.juros_segmentos_default):
        db.delete(segmento)
    db.flush()
    for item in payload.correcao_segmentos_default:
        db.add(
            CorrecaoSegmento(
                processo_id=processo.id, dono_tipo=DonoTipo.PROCESSO_DEFAULT, **item.model_dump()
            )
        )
    for item in payload.juros_segmentos_default:
        db.add(
            JurosSegmento(
                processo_id=processo.id, dono_tipo=DonoTipo.PROCESSO_DEFAULT, **item.model_dump()
            )
        )


@router.get("", response_model=list[ProcessoListItem])
def listar_processos(db: Session = Depends(get_db)) -> list[ProcessoListItem]:
    processos = db.execute(select(Processo)).scalars().all()
    itens = []
    for processo in processos:
        ultima_execucao = db.execute(
            select(CalculoExecucao)
            .where(CalculoExecucao.processo_id == processo.id)
            .order_by(CalculoExecucao.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        itens.append(
            ProcessoListItem(
                id=processo.id,
                numero_processo=processo.numero_processo,
                requerente=processo.requerente,
                requerido=processo.requerido,
                data_calculo=processo.data_calculo,
                ultimo_total_apurado=ultima_execucao.valor_total_apurado if ultima_execucao else None,
            )
        )
    return itens


@router.post("", response_model=ProcessoOut, status_code=201)
def criar_processo(payload: ProcessoCreate, db: Session = Depends(get_db)) -> Processo:
    dados = payload.model_dump(include=set(_CAMPOS_DIRETOS))
    processo = Processo(**dados)
    db.add(processo)
    db.flush()
    _substituir_segmentos_default(db, processo, payload)
    db.commit()
    db.refresh(processo)
    return processo


@router.get("/{processo_id}", response_model=ProcessoOut)
def obter_processo(processo_id: UUID, db: Session = Depends(get_db)) -> Processo:
    return _obter_processo_ou_404(db, processo_id)


@router.put("/{processo_id}", response_model=ProcessoOut)
def atualizar_processo(processo_id: UUID, payload: ProcessoUpdate, db: Session = Depends(get_db)) -> Processo:
    processo = _obter_processo_ou_404(db, processo_id)
    for campo in _CAMPOS_DIRETOS:
        setattr(processo, campo, getattr(payload, campo))
    _substituir_segmentos_default(db, processo, payload)
    db.commit()
    db.refresh(processo)
    return processo


@router.delete("/{processo_id}", status_code=204)
def remover_processo(processo_id: UUID, db: Session = Depends(get_db)) -> None:
    processo = _obter_processo_ou_404(db, processo_id)
    db.delete(processo)
    db.commit()
