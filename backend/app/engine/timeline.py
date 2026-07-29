"""Motor de cálculo — linha do tempo mês a mês de uma parcela (seção 3).

Módulo puro: não faz I/O. Todas as dependências externas (série
histórica de índices, segmentos de correção/juros, paradas) são
recebidas já resolvidas pelo chamador — a camada de serviço é quem lê o
banco e monta essas listas antes de chamar `calcular_parcela`.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import Sequence

from .correcao import segmento_correcao_vigente_em
from .juros import resolver_taxa_mensal, segmento_juros_vigente_em
from .paradas import parada_ativa_em
from .types import (
    BuscarVariacao,
    ContagemJuros,
    CorrecaoSegmento,
    Indice,
    JurosSegmento,
    LinhaMemoria,
    Parcela,
    ParadaExtraordinaria,
    ResultadoCalculo,
    TipoTaxaJuros,
)

getcontext().prec = 28

DUAS_CASAS = Decimal("0.01")


def primeiro_dia_do_mes(d: date) -> date:
    return d.replace(day=1)


def _proximo_mes(competencia: date) -> date:
    if competencia.month == 12:
        return competencia.replace(year=competencia.year + 1, month=1, day=1)
    return competencia.replace(month=competencia.month + 1, day=1)


def _dias_no_mes(competencia: date) -> int:
    proximo = _proximo_mes(competencia)
    return (proximo - competencia).days


def fracao_dias_no_periodo(
    competencia: date, inicio_parcela: date, fim_calculo: date
) -> Decimal:
    """Fração de dias efetivamente decorridos dentro do mês `competencia`
    (seção 3.7). Funciona uniformemente para os três casos: mês cheio no
    meio da linha do tempo (fração = 1), primeiro mês parcial (vencimento
    no meio do mês) e último mês parcial (data do cálculo no meio do
    mês) — inclusive quando os dois casos coincidem no mesmo mês.
    """
    total_dias = _dias_no_mes(competencia)
    inicio_mes = competencia
    fim_mes = competencia.replace(day=total_dias)

    inicio_efetivo = max(inicio_mes, inicio_parcela)
    fim_efetivo = min(fim_mes, fim_calculo)

    if fim_efetivo < inicio_efetivo:
        return Decimal(0)

    dias_efetivos = (fim_efetivo - inicio_efetivo).days + 1
    return Decimal(dias_efetivos) / Decimal(total_dias)


def validar_segmentos(
    segmentos_correcao: Sequence[CorrecaoSegmento],
    segmentos_juros: Sequence[JurosSegmento],
) -> None:
    """Levanta ValueError se houver Selic substitutiva sobreposta a um
    índice de correção diferente de "sem correção" no mesmo período —
    isso duplicaria a correção monetária (seção 3.4).
    """
    for js in segmentos_juros:
        if js.tipo_taxa is not TipoTaxaJuros.SELIC_SUBSTITUTIVA:
            continue
        fim_js = js.data_fim or date.max
        for cs in segmentos_correcao:
            if cs.indice is Indice.SEM_CORRECAO:
                continue
            fim_cs = cs.data_fim or date.max
            inicio_conflito = max(js.data_inicio, cs.data_inicio)
            fim_conflito = min(fim_js, fim_cs)
            if inicio_conflito <= fim_conflito:
                raise ValueError(
                    "Configuração inválida: Selic substitutiva "
                    f"({js.data_inicio} a {js.data_fim or 'aberto'}) se sobrepõe "
                    f"a um índice de correção diferente de 'sem correção' "
                    f"({cs.indice.value}, {cs.data_inicio} a {cs.data_fim or 'aberto'}). "
                    "Configure o segmento de correção desse período como "
                    "'sem correção' para evitar duplicidade — ver seção 3.4."
                )


def calcular_parcela(
    parcela: Parcela,
    segmentos_correcao: Sequence[CorrecaoSegmento],
    segmentos_juros: Sequence[JurosSegmento],
    paradas: Sequence[ParadaExtraordinaria],
    hoje: date,
    buscar_variacao: BuscarVariacao,
    contagem_juros: ContagemJuros = ContagemJuros.PRO_RATA,
    aplicar_art_354_cc: bool = False,
) -> ResultadoCalculo:
    """Calcula a linha do tempo completa de uma parcela mês a mês.

    Devolve o valor apurado (arredondado em 2 casas, ROUND_HALF_UP) e a
    memória de cálculo completa (sem arredondamento intermediário — ver
    seção 3.1). `buscar_variacao` é injetado pelo chamador; o motor não
    acessa banco de dados nem rede.

    Juros moratórios são SIMPLES por padrão (seção 3.3): o motor mantém
    dois acumuladores separados — `saldo_principal` (só recebe correção
    monetária) e `juros_acumulado` (soma simples do juro de cada mês).
    O juro de um mês NUNCA vira base de correção nem de juros do mês
    seguinte — só `saldo_principal` compõe. Isso é o que torna o juro
    "simples" em vez de composto. Quando um segmento é `SELIC_SUBSTITUTIVA`
    (seção 3.4), o `juros_acumulado` corrente é fundido ao principal
    (a Selic passa a corrigir o saldo total de uma vez) e zerado — a
    partir daí o motor volta a tratar o resultado como principal comum.

    `aplicar_art_354_cc` (paridade SOSCálculos, seção 11 — antes uma
    pendência de confirmação jurídica, agora resolvida pelo próprio
    texto de lei): art. 354 do Código Civil determina que, havendo
    capital e juros, o pagamento se imputa primeiro nos juros vencidos e
    só depois no capital. Quando True, cada pagamento abate primeiro
    `juros_acumulado` (até zerar) e só o excedente reduz `saldo_principal`
    — padrão (False) continua abatendo o principal diretamente, como
    já documentado antes.
    """
    if hoje < parcela.vencimento:
        raise ValueError("data do cálculo não pode ser anterior ao vencimento da parcela")

    validar_segmentos(segmentos_correcao, segmentos_juros)

    saldo_principal = parcela.valor_bruto
    juros_acumulado = Decimal(0)
    memoria: list[LinhaMemoria] = []
    competencia = primeiro_dia_do_mes(parcela.vencimento)
    fim = primeiro_dia_do_mes(hoje)
    pagamentos_pendentes = sorted(parcela.pagamentos, key=lambda p: p.data)

    while competencia <= fim:
        # 1. abatimento de pagamentos que caem nesta competência (seção
        # 3.6) — o pagamento reduz o saldo principal diretamente (ver
        # seção 11: imputação de pagamento é um ponto a confirmar
        # juridicamente; este é o default documentado).
        while pagamentos_pendentes and primeiro_dia_do_mes(pagamentos_pendentes[0].data) == competencia:
            pagamento = pagamentos_pendentes.pop(0)
            if aplicar_art_354_cc:
                abate_juros = min(pagamento.valor, juros_acumulado)
                juros_acumulado = juros_acumulado - abate_juros
                saldo_principal = saldo_principal - (pagamento.valor - abate_juros)
            else:
                saldo_principal = saldo_principal - pagamento.valor

        saldo_inicio_mes = saldo_principal + juros_acumulado
        parada = parada_ativa_em(paradas, competencia)

        if saldo_inicio_mes <= 0:
            memoria.append(
                LinhaMemoria(
                    competencia=competencia,
                    saldo_inicio=saldo_inicio_mes,
                    indice=None,
                    variacao_indice=Decimal(0),
                    saldo_corrigido=saldo_inicio_mes,
                    tipo_taxa_juros=None,
                    taxa_juros_mensal=Decimal(0),
                    juros_mes=Decimal(0),
                    saldo_final=saldo_inicio_mes,
                    parada_ativa=bool(parada),
                    quitado=True,
                )
            )
            break

        fator_dias = fracao_dias_no_periodo(competencia, parcela.vencimento, hoje)

        seg_correcao = segmento_correcao_vigente_em(segmentos_correcao, competencia)
        indice = seg_correcao.indice if seg_correcao else None

        seg_juros = segmento_juros_vigente_em(segmentos_juros, competencia)
        tipo_taxa = seg_juros.tipo_taxa if seg_juros else None

        if tipo_taxa is TipoTaxaJuros.SELIC_SUBSTITUTIVA:
            # Seção 3.4: a Selic substitui correção E juros ao mesmo
            # tempo. Funde o juro simples já acumulado ao principal (o
            # saldo total passa a ser corrigido como um só a partir daqui)
            # e ignora o índice de correção configurado para este trecho.
            variacao = buscar_variacao(Indice.SELIC_SIMPLES, competencia)
            base = saldo_principal + juros_acumulado
            saldo_principal = (
                base if (parada and parada.suspende_correcao)
                else base * (Decimal(1) + variacao * fator_dias)
            )
            juros_acumulado = Decimal(0)
            taxa_juros_mensal = Decimal(0)
            juros_mes = Decimal(0)
            saldo_corrigido = saldo_principal
        else:
            variacao = (
                buscar_variacao(indice, competencia)
                if indice is not None and indice is not Indice.SEM_CORRECAO
                else Decimal(0)
            )
            if seg_correcao is not None and not seg_correcao.permite_deflacao and variacao < 0:
                variacao = Decimal(0)
            saldo_principal = (
                saldo_principal
                if (parada and parada.suspende_correcao)
                else saldo_principal * (Decimal(1) + variacao * fator_dias)
            )
            saldo_corrigido = saldo_principal

            if parada and parada.suspende_juros:
                taxa_juros_mensal = Decimal(0)
                juros_mes = Decimal(0)
            elif seg_juros is not None:
                taxa_juros_mensal = resolver_taxa_mensal(seg_juros, competencia, buscar_variacao)
                fator_dias_juros = (
                    fator_dias if contagem_juros is ContagemJuros.PRO_RATA else Decimal(1)
                )
                juros_mes = saldo_corrigido * taxa_juros_mensal * fator_dias_juros
                juros_acumulado = juros_acumulado + juros_mes
            else:
                taxa_juros_mensal = Decimal(0)
                juros_mes = Decimal(0)

        saldo_final = saldo_principal + juros_acumulado

        memoria.append(
            LinhaMemoria(
                competencia=competencia,
                saldo_inicio=saldo_inicio_mes,
                indice=indice,
                variacao_indice=variacao,
                saldo_corrigido=saldo_corrigido,
                tipo_taxa_juros=tipo_taxa,
                taxa_juros_mensal=taxa_juros_mensal,
                juros_mes=juros_mes,
                saldo_final=saldo_final,
                parada_ativa=bool(parada),
            )
        )

        competencia = _proximo_mes(competencia)

    valor_apurado = (saldo_principal + juros_acumulado).quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
    return ResultadoCalculo(valor_apurado=valor_apurado, memoria=tuple(memoria))
