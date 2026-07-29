"""Rotas de cálculo (seção 4.5, passo 4).

`POST /processos/{id}/calcular` roda o motor e devolve os valores
apurados + memória mês a mês, sem persistir nada (pré-visualização).
`POST /processos/{id}/emitir` persiste `calculo_execucao`/`memoria_calculo`
e devolve o PDF. `GET /execucoes/{id}/pdf` regera o PDF de uma emissão
passada a partir da memória já persistida — nunca recalculando."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.calculo_execucao import CalculoExecucao
from app.models.processo import Processo
from app.schemas.calculo import (
    CalculoPreviewOut,
    LinhaMemoriaOut,
    ResultadoAcessorioOut,
    ResultadoDeducaoOut,
    ResultadoParcelaOut,
)
from app.services.calculo_service import calcular_processo
from app.services.emissao_service import emitir_processo
from app.services.pdf_export import gerar_pdf

router = APIRouter(tags=["calculo"])


def _memoria_out(memoria) -> list[LinhaMemoriaOut]:
    return [
        LinhaMemoriaOut(
            competencia=linha.competencia,
            saldo_inicio=linha.saldo_inicio,
            indice=linha.indice,
            variacao_indice=linha.variacao_indice,
            saldo_corrigido=linha.saldo_corrigido,
            tipo_taxa_juros=linha.tipo_taxa_juros,
            taxa_juros_mensal=linha.taxa_juros_mensal,
            juros_mes=linha.juros_mes,
            saldo_final=linha.saldo_final,
            parada_ativa=linha.parada_ativa,
            quitado=linha.quitado,
        )
        for linha in memoria
    ]


@router.post("/processos/{processo_id}/calcular", response_model=CalculoPreviewOut)
def calcular(processo_id: UUID, db: Session = Depends(get_db)) -> CalculoPreviewOut:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")

    try:
        resultado = calcular_processo(db, processo, processo.data_calculo)
    except ValueError as exc:
        # validação do motor (ex.: Selic substitutiva sobreposta a
        # correção, seção 3.4) — erro de configuração do usuário, não bug.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CalculoPreviewOut(
        parcelas=[
            ResultadoParcelaOut(
                parcela_id=parcela_id, valor_apurado=r.valor_apurado, memoria=_memoria_out(r.memoria)
            )
            for parcela_id, r in resultado.resultados_parcelas.items()
        ],
        acessorios=[
            ResultadoAcessorioOut(
                acessorio_id=acessorio_id, valor_apurado=r.valor_apurado, memoria=_memoria_out(r.memoria)
            )
            for acessorio_id, r in resultado.resultados_acessorios.items()
        ],
        deducoes=[
            ResultadoDeducaoOut(
                deducao_id=deducao_id, valor_apurado=r.valor_apurado, memoria=_memoria_out(r.memoria)
            )
            for deducao_id, r in resultado.resultados_deducoes.items()
        ],
        total_geral=resultado.total_geral,
    )


@router.post("/processos/{processo_id}/emitir")
def emitir(processo_id: UUID, db: Session = Depends(get_db)) -> Response:
    processo = db.get(Processo, processo_id)
    if processo is None:
        raise HTTPException(status_code=404, detail="processo não encontrado")

    try:
        execucao = emitir_processo(db, processo, processo.data_calculo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    pdf_bytes = gerar_pdf(db, execucao)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="memoria-calculo-{execucao.id}.pdf"',
            "X-Calculo-Execucao-Id": str(execucao.id),
        },
    )


@router.get("/execucoes/{execucao_id}/pdf")
def pdf_de_execucao(execucao_id: UUID, db: Session = Depends(get_db)) -> Response:
    execucao = db.get(CalculoExecucao, execucao_id)
    if execucao is None:
        raise HTTPException(status_code=404, detail="execução não encontrada")

    pdf_bytes = gerar_pdf(db, execucao)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="memoria-calculo-{execucao.id}.pdf"'},
    )
