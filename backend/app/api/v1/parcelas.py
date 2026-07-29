"""Rotas de `parcela` e `pagamento_parcial` (seção 4.5, passo 2)."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.enums import DonoTipo, TipoPagamentoParcial
from app.models.pagamento_parcial import PagamentoParcial
from app.models.parcela import Parcela
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento, JurosSegmento
from app.schemas.pagamento import PagamentoParcialCreate, PagamentoParcialOut
from app.schemas.parcela import ParcelaCreate, ParcelaOut, ParcelaUpdate
from app.schemas.salario_minimo import GerarPorSalarioMinimoRequest
from app.services.salario_minimo import buscar_valor_vigente

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


def _vencimentos_em_serie(inicio: date, fim: date, fim_mes: bool) -> list[date]:
    """Um vencimento por mês entre `inicio` e `fim` (inclusive, por
    ano-mês) — mesmo dia de `inicio` em cada mês (limitado ao último dia
    de meses mais curtos), ou o último dia do mês se `fim_mes`. Mesma
    lógica do gerador "Preenchimento em Série" do frontend, replicada
    aqui porque "Salário Mínimo" precisa do valor absoluto por
    competência, que só o backend conhece."""
    vencimentos: list[date] = []
    ano, mes = inicio.year, inicio.month
    dia_fixo = inicio.day
    guarda = 0
    while (ano, mes) <= (fim.year, fim.month) and guarda < 1200:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = ultimo_dia if fim_mes else min(dia_fixo, ultimo_dia)
        vencimentos.append(date(ano, mes, dia))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
        guarda += 1
    return vencimentos


@router.post("/processos/{processo_id}/parcelas/gerar-por-salario-minimo", response_model=list[ParcelaOut], status_code=201)
def gerar_parcelas_por_salario_minimo(
    processo_id: UUID, payload: GerarPorSalarioMinimoRequest, db: Session = Depends(get_db)
) -> list[Parcela]:
    """Botão "Salário Mínimo" do passo 2 — uma parcela por mês, com
    `valor_bruto = percentual_salario * valor_vigente_na_competencia`
    (seção 3.9/4). Valida TODOS os meses antes de criar QUALQUER
    parcela — nunca gera metade da série e falha no meio."""
    _obter_processo_ou_404(db, processo_id)
    if payload.data_final < payload.data_inicial:
        raise HTTPException(status_code=422, detail="Data Final não pode ser anterior à Data Inicial")

    vencimentos = _vencimentos_em_serie(payload.data_inicial, payload.data_final, payload.fim_mes)

    valores_por_vencimento: dict[date, Decimal] = {}
    faltando: list[str] = []
    for vencimento in vencimentos:
        competencia = vencimento.replace(day=1)
        valor_vigente = buscar_valor_vigente(db, competencia)
        if valor_vigente is None:
            faltando.append(competencia.strftime("%m/%Y"))
        else:
            valores_por_vencimento[vencimento] = valor_vigente
    if faltando:
        raise HTTPException(
            status_code=422,
            detail=(
                "Não há salário mínimo cadastrado para: " + ", ".join(faltando) +
                ". Cadastre o valor vigente dessas competências antes de gerar."
            ),
        )

    percentual = Decimal(payload.percentual_salario)
    percentual_pago = Decimal(payload.percentual_pago) if payload.percentual_pago else None

    criadas: list[Parcela] = []
    for vencimento in vencimentos:
        valor_bruto = (percentual * valores_por_vencimento[vencimento]).quantize(Decimal("0.01"))
        parcela = Parcela(
            processo_id=processo_id,
            vencimento=vencimento,
            historico=payload.historico,
            valor_bruto=valor_bruto,
            usa_correcao_default=payload.usa_correcao_default,
            usa_juros_default=payload.usa_juros_default,
            multa_percentual=payload.multa_percentual,
        )
        db.add(parcela)
        db.flush()
        for item in payload.correcao_segmentos_override:
            db.add(CorrecaoSegmento(parcela_id=parcela.id, dono_tipo=DonoTipo.PARCELA_OVERRIDE, **item.model_dump()))
        for item in payload.juros_segmentos_override:
            db.add(JurosSegmento(parcela_id=parcela.id, dono_tipo=DonoTipo.PARCELA_OVERRIDE, **item.model_dump()))
        if percentual_pago:
            db.add(
                PagamentoParcial(
                    parcela_id=parcela.id,
                    data=vencimento,
                    valor=(valor_bruto * percentual_pago).quantize(Decimal("0.01")),
                    tipo=TipoPagamentoParcial.PAGAMENTO,
                    descricao="% pago gerado pelo preenchimento por Salário Mínimo",
                )
            )
        criadas.append(parcela)

    db.commit()
    for parcela in criadas:
        db.refresh(parcela)
    return criadas


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
