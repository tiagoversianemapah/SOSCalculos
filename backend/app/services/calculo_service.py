"""Resolve dados do banco para os tipos do motor e orquestra o cálculo
completo de um processo — parcelas + acessórios + total (seção 3.9/6.1).

Nenhuma regra de negócio mora aqui além de "buscar dado e montar o value
object que o motor espera" (invariante 12.1.7): a decisão de como
calcular é 100% do `app/engine/`, que nunca acessa o banco diretamente.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import acessorios as motor_acessorios
from app.engine import timeline as motor_timeline
from app.engine.types import (
    Acessorio as AcessorioEngine,
    BaseCalculoAcessorio,
    BuscarVariacao,
    CorrecaoSegmento as CorrecaoSegmentoEngine,
    Indice,
    JurosSegmento as JurosSegmentoEngine,
    Pagamento as PagamentoEngine,
    Parcela as ParcelaEngine,
    ParadaExtraordinaria as ParadaEngine,
    ResultadoCalculo,
    TipoTaxaJuros,
)
from app.models.acessorio import Acessorio
from app.models.deducao import Deducao
from app.models.enums import TipoAtualizacaoDeducao
from app.models.indice_serie_valor import IndiceSerieValor
from app.models.parada import ParadaExtraordinaria
from app.models.parcela import Parcela
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento, JurosSegmento


def criar_buscar_variacao(db: Session) -> BuscarVariacao:
    """Fábrica de `buscar_variacao` ligada à sessão do banco — o motor
    nunca acessa o banco diretamente (seção 3.1)."""

    def _buscar(indice, competencia: date) -> Decimal:
        variacao = db.execute(
            select(IndiceSerieValor.variacao_percentual).where(
                IndiceSerieValor.indice == indice,
                IndiceSerieValor.competencia == competencia,
                IndiceSerieValor.tribunal_codigo == "",
                IndiceSerieValor.superseded_por.is_(None),
            )
        ).scalar_one_or_none()
        if variacao is None:
            # Defasagem de publicação (seção 5): competência sem índice
            # publicado ainda vira variação zero, nunca falha.
            return Decimal(0)
        return variacao

    return _buscar


def _segmentos_correcao_engine(segmentos: Sequence[CorrecaoSegmento]) -> list[CorrecaoSegmentoEngine]:
    # Campo "Compor com Selic" (seção 0/2, paridade SOSCálculos): quando
    # marcado, a Selic substitui a correção E os juros nesse período de
    # uma vez só (mesma regra de SELIC_SUBSTITUTIVA, seção 3.4) — então
    # aqui o segmento vira "sem correção" e o juros correspondente é
    # gerado à parte em `_segmentos_juros_engine`.
    return [
        CorrecaoSegmentoEngine(
            indice=Indice.SEM_CORRECAO if s.compor_com_selic else s.indice,
            data_inicio=s.data_inicio,
            data_fim=s.data_fim,
            permite_deflacao=s.permite_deflacao,
        )
        for s in sorted(segmentos, key=lambda s: s.ordem)
    ]


def _segmentos_juros_engine(
    segmentos: Sequence[JurosSegmento], correcao_segmentos: Sequence[CorrecaoSegmento] = ()
) -> list[JurosSegmentoEngine]:
    # Segmentos de Selic gerados por "Compor com Selic" vêm primeiro —
    # `segmento_juros_vigente_em` devolve o primeiro que casar com a
    # competência, e essas datas são as que o usuário escolheu
    # especificamente pra esse efeito (ex.: preset "Tema 1368/STJ").
    gerados_por_selic = [
        JurosSegmentoEngine(tipo_taxa=TipoTaxaJuros.SELIC_SUBSTITUTIVA, data_inicio=s.data_inicio, data_fim=s.data_fim)
        for s in correcao_segmentos
        if s.compor_com_selic
    ]
    configurados = [
        JurosSegmentoEngine(
            tipo_taxa=s.tipo_taxa, data_inicio=s.data_inicio, data_fim=s.data_fim, taxa_valor=s.taxa_valor
        )
        for s in sorted(segmentos, key=lambda s: s.ordem)
    ]
    return gerados_por_selic + configurados


def _paradas_engine(paradas: Sequence[ParadaExtraordinaria]) -> list[ParadaEngine]:
    return [
        ParadaEngine(
            data_inicio=p.data_inicio,
            data_fim=p.data_fim,
            suspende_correcao=p.suspende_correcao,
            suspende_juros=p.suspende_juros,
            motivo=p.motivo,
        )
        for p in paradas
    ]


def _segmentos_correcao_da_parcela(parcela: Parcela, processo: Processo) -> list[CorrecaoSegmentoEngine]:
    if parcela.usa_correcao_default:
        return _segmentos_correcao_engine(processo.correcao_segmentos_default)
    return _segmentos_correcao_engine(parcela.correcao_segmentos_override)


def _segmentos_juros_da_parcela(parcela: Parcela, processo: Processo) -> list[JurosSegmentoEngine]:
    if parcela.usa_juros_default:
        return _segmentos_juros_engine(processo.juros_segmentos_default, processo.correcao_segmentos_default)
    correcao_da_parcela = (
        processo.correcao_segmentos_default if parcela.usa_correcao_default else parcela.correcao_segmentos_override
    )
    return _segmentos_juros_engine(parcela.juros_segmentos_override, correcao_da_parcela)


def _segmentos_correcao_do_acessorio(acessorio: Acessorio, processo: Processo) -> list[CorrecaoSegmentoEngine]:
    if acessorio.usa_correcao_default:
        return _segmentos_correcao_engine(processo.correcao_segmentos_default)
    return _segmentos_correcao_engine(acessorio.correcao_segmentos_override)


def _segmentos_juros_do_acessorio(acessorio: Acessorio, processo: Processo) -> list[JurosSegmentoEngine]:
    if acessorio.usa_juros_default:
        return _segmentos_juros_engine(processo.juros_segmentos_default, processo.correcao_segmentos_default)
    correcao_do_acessorio = (
        processo.correcao_segmentos_default if acessorio.usa_correcao_default else acessorio.correcao_segmentos_override
    )
    return _segmentos_juros_engine(acessorio.juros_segmentos_override, correcao_do_acessorio)


def _segmentos_correcao_da_deducao(deducao: Deducao, processo: Processo) -> list[CorrecaoSegmentoEngine]:
    if deducao.usa_correcao_default:
        return _segmentos_correcao_engine(processo.correcao_segmentos_default)
    return _segmentos_correcao_engine(deducao.correcao_segmentos_override)


def _segmentos_juros_da_deducao(deducao: Deducao, processo: Processo) -> list[JurosSegmentoEngine]:
    if deducao.usa_juros_default:
        return _segmentos_juros_engine(processo.juros_segmentos_default, processo.correcao_segmentos_default)
    correcao_da_deducao = (
        processo.correcao_segmentos_default if deducao.usa_correcao_default else deducao.correcao_segmentos_override
    )
    return _segmentos_juros_engine(deducao.juros_segmentos_override, correcao_da_deducao)


def _data_evento_deducao(deducao: Deducao) -> date | None:
    # "Atualização" (paridade SOSCálculos): qual data ancora a correção
    # da dedução. DATA_CALCULO significa "o valor já está em termos de
    # hoje" — sem passar pela linha do tempo (mesmo efeito de
    # data_evento=None no Acessorio). DATA_LEVANTAMENTO e OUTRA_DATA
    # usam a mesma âncora (`data_atualizacao`, digitada manualmente).
    if deducao.atualizacao_tipo is TipoAtualizacaoDeducao.DATA_CALCULO:
        return None
    if deducao.atualizacao_tipo is TipoAtualizacaoDeducao.DATA_INICIAL:
        return deducao.data_inicial
    return deducao.data_atualizacao


def _montar_deducao_engine(deducao: Deducao) -> AcessorioEngine:
    return AcessorioEngine(
        percentual=None,
        valor_fixo=deducao.valor,
        base_calculo=BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO,
        data_evento=_data_evento_deducao(deducao),
    )


def _paradas_da_parcela(parcela: Parcela, processo: Processo) -> list[ParadaEngine]:
    # Paradas do processo aplicam a todas as parcelas; paradas da própria
    # parcela se somam a elas (seção 3.5/seção 2 — `parada_extraordinaria`
    # com `parcela_id` preenchido é específica daquela parcela).
    return _paradas_engine(processo.paradas) + _paradas_engine(parcela.paradas)


def montar_parcela_engine(parcela: Parcela) -> ParcelaEngine:
    pagamentos = tuple(
        PagamentoEngine(data=p.data, valor=p.valor)
        for p in sorted(parcela.pagamentos, key=lambda p: p.data)
    )
    return ParcelaEngine(vencimento=parcela.vencimento, valor_bruto=parcela.valor_bruto, pagamentos=pagamentos)


def calcular_parcela_db(db: Session, parcela: Parcela, processo: Processo, hoje: date) -> ResultadoCalculo:
    """Roda o motor para uma única parcela, com os dados já resolvidos
    do banco. Pode levantar `ValueError` (validação do motor, ex.:
    Selic substitutiva sobreposta a correção — seção 3.4)."""
    return motor_timeline.calcular_parcela(
        montar_parcela_engine(parcela),
        _segmentos_correcao_da_parcela(parcela, processo),
        _segmentos_juros_da_parcela(parcela, processo),
        _paradas_da_parcela(parcela, processo),
        hoje,
        criar_buscar_variacao(db),
        contagem_juros=processo.contagem_juros,
        aplicar_art_354_cc=processo.aplicar_art_354_cc,
    )


def _montar_acessorio_engine(acessorio: Acessorio) -> AcessorioEngine:
    return AcessorioEngine(
        percentual=acessorio.percentual,
        valor_fixo=acessorio.valor_fixo,
        base_calculo=acessorio.base_calculo,
        data_evento=acessorio.data_evento,
        valor_diario=acessorio.valor_diario,
        data_inicio_acumulo=acessorio.data_inicio_acumulo,
    )


class ResultadoProcesso:
    """Agrega o resultado de um cálculo completo de processo (seção 3.9),
    pronto para a camada de API montar a resposta ou persistir a
    `memoria_calculo` (em `emitir`)."""

    def __init__(
        self,
        resultados_parcelas: dict[uuid.UUID, ResultadoCalculo],
        resultados_acessorios: dict[uuid.UUID, ResultadoCalculo],
        resultados_deducoes: dict[uuid.UUID, ResultadoCalculo],
        total_geral: Decimal,
    ) -> None:
        self.resultados_parcelas = resultados_parcelas
        self.resultados_acessorios = resultados_acessorios
        self.resultados_deducoes = resultados_deducoes
        self.total_geral = total_geral


def calcular_processo(db: Session, processo: Processo, hoje: date) -> ResultadoProcesso:
    """Calcula todas as parcelas + acessórios do processo (seção 3.9).

    Pré-visualização pura — não persiste `memoria_calculo` (isso só
    acontece em `emitir`, seção 4/4.5, para poder reconstruir um PDF já
    emitido mesmo que os índices mudem depois).
    """
    resultados_parcelas: dict[uuid.UUID, ResultadoCalculo] = {
        parcela.id: calcular_parcela_db(db, parcela, processo, hoje) for parcela in processo.parcelas
    }

    total_liquido_parcelas = motor_acessorios.calcular_total_processo(
        list(resultados_parcelas.values()), []
    )
    total_principal_sem_correcao = sum((p.valor_bruto for p in processo.parcelas), Decimal(0))

    paradas_default = _paradas_engine(processo.paradas)
    buscar_variacao = criar_buscar_variacao(db)

    resultados_acessorios: dict[uuid.UUID, ResultadoCalculo] = {}
    for acessorio in processo.acessorios:
        total_saldo_remanescente = None
        if acessorio.base_calculo is BaseCalculoAcessorio.SALDO_REMANESCENTE_EM_DATA_EVENTO:
            assert acessorio.data_evento is not None
            total_saldo_remanescente = sum(
                (
                    calcular_parcela_db(db, parcela, processo, acessorio.data_evento).valor_apurado
                    for parcela in processo.parcelas
                ),
                Decimal(0),
            )
        resultados_acessorios[acessorio.id] = motor_acessorios.calcular_acessorio(
            _montar_acessorio_engine(acessorio),
            total_liquido_parcelas,
            total_principal_sem_correcao,
            hoje,
            _segmentos_correcao_do_acessorio(acessorio, processo),
            _segmentos_juros_do_acessorio(acessorio, processo),
            paradas_default,
            buscar_variacao,
            total_saldo_remanescente_em_data_evento=total_saldo_remanescente,
            contagem_juros=processo.contagem_juros,
            valor_causa=processo.valor_causa,
        )

    resultados_deducoes: dict[uuid.UUID, ResultadoCalculo] = {}
    for deducao in processo.deducoes:
        resultados_deducoes[deducao.id] = motor_acessorios.calcular_acessorio(
            _montar_deducao_engine(deducao),
            total_liquido_parcelas,
            total_principal_sem_correcao,
            hoje,
            _segmentos_correcao_da_deducao(deducao, processo),
            _segmentos_juros_da_deducao(deducao, processo),
            paradas_default,
            buscar_variacao,
            contagem_juros=processo.contagem_juros,
        )

    total_geral = motor_acessorios.calcular_total_processo(
        list(resultados_parcelas.values()), list(resultados_acessorios.values())
    )
    total_deducoes = sum((r.valor_apurado for r in resultados_deducoes.values()), Decimal(0))
    total_geral = total_geral - total_deducoes

    return ResultadoProcesso(resultados_parcelas, resultados_acessorios, resultados_deducoes, total_geral)
