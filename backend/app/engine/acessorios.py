"""Cálculo de acessórios e do total do processo (seção 3.9)."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Sequence

from .timeline import DUAS_CASAS, calcular_parcela
from .types import (
    Acessorio,
    BaseCalculoAcessorio,
    BuscarVariacao,
    ContagemJuros,
    CorrecaoSegmento,
    JurosSegmento,
    Parcela,
    ParadaExtraordinaria,
    ResultadoCalculo,
)


def _fim_do_mes(d: date) -> date:
    ultimo_dia = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=ultimo_dia)


def _marcos_por_competencia(data_inicio: date, data_fim: date) -> list[date]:
    """[data_inicio, fim do 1º mês, fim do 2º mês, ..., data_fim] —
    confirmado com cálculo real do SOSCálculos (multa "Diária
    (Competência)", 01/01 a 01/04/2024 → marcos 01/01, 31/01, 29/02,
    31/03, 01/04; dias por competência = diferença entre marcos
    consecutivos: 30, 29, 31, 1 — soma 91, igual ao total "sem +1" da
    "Diária (Data final)", só distribuído por mês)."""
    marcos = [data_inicio]
    atual = data_inicio
    while True:
        fim_mes_atual = _fim_do_mes(atual)
        proximo_mes = fim_mes_atual + timedelta(days=1)
        if proximo_mes > data_fim:
            marcos.append(data_fim)
            break
        marcos.append(fim_mes_atual)
        atual = proximo_mes
    return marcos


def _buckets_diaria_competencia(data_inicio: date, data_fim: date) -> list[tuple[date, int]]:
    """Uma (âncora, dias) por competência — âncora é o 1º dia do mês em
    que aquele trecho começa (ou a própria `data_inicio` no primeiro),
    usada como `data_evento` da sub-linha de correção/juros daquele
    trecho (ver `calcular_acessorio`)."""
    marcos = _marcos_por_competencia(data_inicio, data_fim)
    buckets = []
    for i in range(len(marcos) - 1):
        dias = (marcos[i + 1] - marcos[i]).days
        ancora = marcos[i] if i == 0 else marcos[i] + timedelta(days=1)
        buckets.append((ancora, dias))
    return buckets


def _proximo_mes(d: date) -> date:
    """Mesmo dia-do-mês, um mês à frente — recua pro último dia do mês
    destino se ele não tiver esse dia (ex.: 31/01 -> 29/02)."""
    ano = d.year + (1 if d.month == 12 else 0)
    mes = 1 if d.month == 12 else d.month + 1
    ultimo_dia_mes_destino = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia_mes_destino))


def _marcos_mensais(data_inicio: date, data_fim: date) -> list[date]:
    """Um marco por mês vencido — começa em `data_inicio` + 1 mês (mesmo
    dia do mês, ajustado se o destino não tiver esse dia) e segue mês a
    mês até `data_fim` inclusive. Confirmado com cálculo real do
    SOSCálculos (multa "Mensal", 01/01/2024 a 01/04/2024 → marcos
    01/02, 01/03, 01/04 — 3 lançamentos de valor_mensal cada)."""
    marcos = []
    atual = _proximo_mes(data_inicio)
    while atual <= data_fim:
        marcos.append(atual)
        atual = _proximo_mes(atual)
    return marcos


def calcular_acessorio(
    acessorio: Acessorio,
    total_liquido_parcelas: Decimal,
    total_principal_sem_correcao: Decimal,
    hoje: date,
    segmentos_correcao: Sequence[CorrecaoSegmento],
    segmentos_juros: Sequence[JurosSegmento],
    paradas: Sequence[ParadaExtraordinaria],
    buscar_variacao: BuscarVariacao,
    total_saldo_remanescente_em_data_evento: Optional[Decimal] = None,
    contagem_juros: ContagemJuros = ContagemJuros.PRO_RATA,
    valor_causa: Optional[Decimal] = None,
) -> ResultadoCalculo:
    """Calcula o valor de um acessório.

    Se `data_evento` não estiver preenchida, devolve o valor-base direto
    (sem linha do tempo). Se estiver preenchida, o valor-base passa pela
    mesma linha do tempo de correção/juros do motor principal a partir
    daquela data até `hoje` (seção 3.9).

    `total_saldo_remanescente_em_data_evento` (art. 523 CPC com depósito
    parcial tempestivo, seção 3.9): o chamador já rodou `calcular_parcela`
    de cada parcela com `hoje = acessorio.data_evento` e somou os
    `valor_apurado` — o motor não recalcula isso aqui, só usa o total
    pronto como base quando `base_calculo = SALDO_REMANESCENTE_EM_DATA_EVENTO`.
    """
    if acessorio.valor_diario is not None and acessorio.diaria_por_competencia:
        # Multa "Diária (Competência)" — diferente da "Data final" (um
        # valor único ancorado na Data Fim), quebra em uma sub-linha por
        # mês civil, cada uma corrigida/rendendo juros a partir do 1º dia
        # daquele mês (ou de data_inicio_acumulo, no primeiro trecho) até
        # `hoje` — confirmado com cálculo real (seção 3.9). Cada sub-linha
        # reaproveita `calcular_parcela` como se fosse uma mini-parcela;
        # os resultados são somados e as memórias concatenadas.
        assert acessorio.data_inicio_acumulo is not None
        assert acessorio.data_evento is not None
        buckets = _buckets_diaria_competencia(acessorio.data_inicio_acumulo, acessorio.data_evento)
        valor_total = Decimal(0)
        memoria_total: list = []
        for ancora, dias in buckets:
            valor_bucket = acessorio.valor_diario * Decimal(dias)
            resultado_bucket = calcular_parcela(
                Parcela(vencimento=ancora, valor_bruto=valor_bucket),
                segmentos_correcao,
                segmentos_juros,
                paradas,
                hoje,
                buscar_variacao,
                contagem_juros=contagem_juros,
            )
            valor_total += resultado_bucket.valor_apurado
            memoria_total.extend(resultado_bucket.memoria)
        return ResultadoCalculo(valor_apurado=valor_total, memoria=tuple(memoria_total))

    if acessorio.valor_mensal is not None:
        # Multa "Mensal" — um lançamento de valor_mensal por mês vencido
        # entre data_inicio_acumulo e data_evento, cada um corrigido a
        # partir da sua própria data até `hoje` (confirmado com cálculo
        # real, seção 3.9). Mesmo mecanismo de reuso de calcular_parcela
        # das outras multas por sub-linha.
        assert acessorio.data_inicio_acumulo is not None
        assert acessorio.data_evento is not None
        marcos = _marcos_mensais(acessorio.data_inicio_acumulo, acessorio.data_evento)
        valor_total = Decimal(0)
        memoria_total = []
        for ancora in marcos:
            resultado_marco = calcular_parcela(
                Parcela(vencimento=ancora, valor_bruto=acessorio.valor_mensal),
                segmentos_correcao,
                segmentos_juros,
                paradas,
                hoje,
                buscar_variacao,
                contagem_juros=contagem_juros,
            )
            valor_total += resultado_marco.valor_apurado
            memoria_total.extend(resultado_marco.memoria)
        return ResultadoCalculo(valor_apurado=valor_total, memoria=tuple(memoria_total))

    if acessorio.base_calculo is BaseCalculoAcessorio.TOTAL_LIQUIDO_PARCELAS:
        assert acessorio.percentual is not None
        valor_base = total_liquido_parcelas * acessorio.percentual
    elif acessorio.base_calculo is BaseCalculoAcessorio.VALOR_PRINCIPAL_SEM_CORRECAO:
        assert acessorio.percentual is not None
        valor_base = total_principal_sem_correcao * acessorio.percentual
    elif acessorio.base_calculo is BaseCalculoAcessorio.SALDO_REMANESCENTE_EM_DATA_EVENTO:
        assert acessorio.percentual is not None
        assert total_saldo_remanescente_em_data_evento is not None
        valor_base = total_saldo_remanescente_em_data_evento * acessorio.percentual
    elif acessorio.base_calculo is BaseCalculoAcessorio.VALOR_DA_CAUSA:
        assert acessorio.percentual is not None
        if valor_causa is None:
            raise ValueError(
                "Configuração inválida: acessório usa base 'Sobre o Valor da Causa' mas "
                "'Valor da Causa' não foi preenchido no cadastro do processo (passo 1)."
            )
        valor_base = valor_causa * acessorio.percentual
    elif acessorio.valor_diario is not None:
        # Multa "Diária (Data final)" — dias corridos entre
        # data_inicio_acumulo e data_evento, sem +1 (confirmado com
        # cálculo real do SOSCálculos: 01/01 a 01/03/2024 = 60 dias).
        assert acessorio.data_inicio_acumulo is not None
        assert acessorio.data_evento is not None
        dias = (acessorio.data_evento - acessorio.data_inicio_acumulo).days
        valor_base = acessorio.valor_diario * Decimal(dias)
    else:
        assert acessorio.valor_fixo is not None
        valor_base = acessorio.valor_fixo

    if acessorio.data_evento is None:
        valor_apurado = valor_base.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
        return ResultadoCalculo(valor_apurado=valor_apurado, memoria=())

    parcela_sintetica = Parcela(vencimento=acessorio.data_evento, valor_bruto=valor_base)
    return calcular_parcela(
        parcela_sintetica,
        segmentos_correcao,
        segmentos_juros,
        paradas,
        hoje,
        buscar_variacao,
        contagem_juros=contagem_juros,
    )


def calcular_total_processo(
    resultados_parcelas: Sequence[ResultadoCalculo],
    resultados_acessorios: Sequence[ResultadoCalculo],
) -> Decimal:
    """Soma o total líquido do processo: todas as parcelas + todos os
    acessórios, já calculados. Arredonda só no total final.
    """
    total = sum((r.valor_apurado for r in resultados_parcelas), Decimal(0))
    total += sum((r.valor_apurado for r in resultados_acessorios), Decimal(0))
    return total.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
