"""Persiste uma execução completa do cálculo — `calculo_execucao` +
`memoria_calculo` (seção 4/4.5, `POST /processos/{id}/emitir`).

Diferente de `calculo_service.calcular_processo` (pré-visualização, não
persiste nada), isto roda quando o usuário confirma a emissão: cria um
`calculo_execucao_id` novo e grava a `memoria_calculo` completa ANTES de
qualquer renderização de PDF — é isso que permite reconstruir
exatamente o PDF de uma emissão passada depois (seção 8), mesmo que a
série de índice seja corrigida pelo BCB no meio do caminho.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.engine.types import LinhaMemoria
from app.models.calculo_execucao import CalculoExecucao
from app.models.memoria_calculo import MemoriaCalculo
from app.models.processo import Processo

from .calculo_service import calcular_processo


def _registro_da_linha(
    linha: LinhaMemoria,
    *,
    calculo_execucao_id,
    parcela_id=None,
    acessorio_id=None,
    deducao_id=None,
) -> MemoriaCalculo:
    return MemoriaCalculo(
        calculo_execucao_id=calculo_execucao_id,
        parcela_id=parcela_id,
        acessorio_id=acessorio_id,
        deducao_id=deducao_id,
        competencia=linha.competencia,
        saldo_inicio_mes=linha.saldo_inicio,
        indice_aplicado=linha.indice,
        variacao_indice=linha.variacao_indice,
        saldo_corrigido=linha.saldo_corrigido,
        taxa_juros_aplicada=linha.taxa_juros_mensal,
        juros_mes=linha.juros_mes,
        saldo_final_mes=linha.saldo_final,
        parada_ativa=linha.parada_ativa,
    )


def emitir_processo(db: Session, processo: Processo, hoje: date) -> CalculoExecucao:
    """Roda o motor, persiste `calculo_execucao` + `memoria_calculo`, e
    atualiza o cache `parcela.valor_apurado`. Pode levantar `ValueError`
    (validação do motor, seção 3.4) — o chamador decide o status HTTP.
    """
    resultado = calcular_processo(db, processo, hoje)

    execucao = CalculoExecucao(
        processo_id=processo.id, data_calculo=hoje, valor_total_apurado=resultado.total_geral
    )
    db.add(execucao)
    db.flush()

    for parcela in processo.parcelas:
        resultado_parcela = resultado.resultados_parcelas[parcela.id]
        for linha in resultado_parcela.memoria:
            db.add(_registro_da_linha(linha, calculo_execucao_id=execucao.id, parcela_id=parcela.id))
        parcela.valor_apurado = resultado_parcela.valor_apurado

    for acessorio in processo.acessorios:
        resultado_acessorio = resultado.resultados_acessorios[acessorio.id]
        if resultado_acessorio.memoria:
            for linha in resultado_acessorio.memoria:
                db.add(
                    _registro_da_linha(linha, calculo_execucao_id=execucao.id, acessorio_id=acessorio.id)
                )
        else:
            # Sem data_evento: base não depende de índice/tempo — uma
            # linha sintética única mantém o mesmo invariante das
            # parcelas ("valor_apurado histórico = saldo_final_mes da
            # última linha"), sem precisar de outra tabela.
            db.add(
                MemoriaCalculo(
                    calculo_execucao_id=execucao.id,
                    acessorio_id=acessorio.id,
                    competencia=hoje.replace(day=1),
                    saldo_inicio_mes=resultado_acessorio.valor_apurado,
                    indice_aplicado=None,
                    variacao_indice=Decimal(0),
                    saldo_corrigido=resultado_acessorio.valor_apurado,
                    taxa_juros_aplicada=Decimal(0),
                    juros_mes=Decimal(0),
                    saldo_final_mes=resultado_acessorio.valor_apurado,
                    parada_ativa=False,
                )
            )

    for deducao in processo.deducoes:
        resultado_deducao = resultado.resultados_deducoes[deducao.id]
        if resultado_deducao.memoria:
            for linha in resultado_deducao.memoria:
                db.add(
                    _registro_da_linha(linha, calculo_execucao_id=execucao.id, deducao_id=deducao.id)
                )
        else:
            # "Atualização = Data do Cálculo": sem linha do tempo, mesma
            # linha sintética única já usada pra acessório sem data_evento.
            db.add(
                MemoriaCalculo(
                    calculo_execucao_id=execucao.id,
                    deducao_id=deducao.id,
                    competencia=hoje.replace(day=1),
                    saldo_inicio_mes=resultado_deducao.valor_apurado,
                    indice_aplicado=None,
                    variacao_indice=Decimal(0),
                    saldo_corrigido=resultado_deducao.valor_apurado,
                    taxa_juros_aplicada=Decimal(0),
                    juros_mes=Decimal(0),
                    saldo_final_mes=resultado_deducao.valor_apurado,
                    parada_ativa=False,
                )
            )

    db.commit()
    db.refresh(execucao)
    return execucao
