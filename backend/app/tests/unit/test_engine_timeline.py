"""Casos de referência obrigatórios do motor de cálculo — seção 7 da
especificação técnica (especificacao-tecnica-motor-calculo-judicial.md).

Cada teste compara o valor_apurado final. Valores esperados foram
calculados de forma independente (script isolado, não a partir deste
motor) antes de serem hardcoded aqui — ver histórico de desenvolvimento.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.engine.acessorios import calcular_acessorio, calcular_total_processo
from app.engine.timeline import calcular_parcela
from app.engine.types import (
    Acessorio,
    BaseCalculoAcessorio,
    ContagemJuros,
    CorrecaoSegmento,
    Indice,
    JurosSegmento,
    Pagamento,
    Parcela,
    ParadaExtraordinaria,
    ResultadoCalculo,
    TipoTaxaJuros,
)
from app.tests.fixtures.indices_fake import criar_buscar_variacao


def test_caso_1_indice_unico_sem_juros():
    """Correção monetária composta com um único índice do início ao fim."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.02"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.005"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("1035.35")
    assert len(resultado.memoria) == 3


def test_caso_2_troca_de_indice_no_meio_do_periodo():
    """Correção monetária com dois segmentos de índices diferentes em sequência."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [
        CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), date(2024, 1, 31)),
        CorrecaoSegmento(Indice.IGP_M, date(2024, 2, 1), None),
    ]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IGP_M, date(2024, 2, 1)): Decimal("0.03"),
        (Indice.IGP_M, date(2024, 3, 1)): Decimal("0.02"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("1061.11")
    assert resultado.memoria[0].indice is Indice.IPCA
    assert resultado.memoria[1].indice is Indice.IGP_M
    assert resultado.memoria[2].indice is Indice.IGP_M


def test_caso_3_juros_fixos_simples_sem_correcao():
    """Juros simples (não capitalizam) sobre saldo sem correção monetária.

    Verifica explicitamente que o motor NÃO compõe juros sobre juros:
    o resultado deve ser 1000 + 10 + 10 + 10 = 1030.00 (linear), não
    1030.30 (que seria o resultado se o juro do mês anterior virasse
    base de cálculo do juro seguinte — ver seção 3.3).
    """
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_juros = [
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), None, taxa_valor=Decimal("0.01"))
    ]
    buscar = criar_buscar_variacao({})  # nenhuma variação de índice deveria ser consultada

    resultado = calcular_parcela(parcela, [], segmentos_juros, [], date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("1030.00")
    assert resultado.memoria[0].juros_mes == Decimal("10.00")
    assert resultado.memoria[1].juros_mes == Decimal("10.00")
    assert resultado.memoria[2].juros_mes == Decimal("10.00")


def test_caso_4_correcao_e_juros_com_dois_segmentos_cada_em_datas_diferentes():
    """Correção troca de índice em março; juros trocam de taxa em abril —
    as duas trocas acontecem em datas diferentes uma da outra."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [
        CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), date(2024, 2, 29)),
        CorrecaoSegmento(Indice.IGP_M, date(2024, 3, 1), None),
    ]
    segmentos_juros = [
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), date(2024, 3, 31), taxa_valor=Decimal("0.005")),
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 4, 1), None, taxa_valor=Decimal("0.01")),
    ]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IGP_M, date(2024, 3, 1)): Decimal("0.02"),
        (Indice.IGP_M, date(2024, 4, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, segmentos_juros, [], date(2024, 4, 30), buscar)

    assert resultado.valor_apurado == Decimal("1076.77")
    assert len(resultado.memoria) == 4


def test_caso_5_selic_substitutiva_parcial():
    """Selic substitutiva (correção + juros embutidos) a partir de fevereiro;
    correção e juros normais em janeiro."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [
        CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), date(2024, 1, 31)),
        CorrecaoSegmento(Indice.SEM_CORRECAO, date(2024, 2, 1), None),
    ]
    segmentos_juros = [
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), date(2024, 1, 31), taxa_valor=Decimal("0.005")),
        JurosSegmento(TipoTaxaJuros.SELIC_SUBSTITUTIVA, date(2024, 2, 1), None),
    ]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.SELIC_SIMPLES, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.SELIC_SIMPLES, date(2024, 3, 1)): Decimal("0.008"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, segmentos_juros, [], date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("1033.40")
    assert resultado.memoria[1].tipo_taxa_juros is TipoTaxaJuros.SELIC_SUBSTITUTIVA
    assert resultado.memoria[1].juros_mes == Decimal("0")


def test_caso_5b_validacao_rejeita_selic_substitutiva_sobreposta_a_correcao():
    """Selic substitutiva sobreposta a um índice de correção diferente de
    'sem correção' deve ser rejeitada (duplicaria a correção) — seção 3.4."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    segmentos_juros = [JurosSegmento(TipoTaxaJuros.SELIC_SUBSTITUTIVA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({})

    with pytest.raises(ValueError, match="Selic substitutiva"):
        calcular_parcela(parcela, segmentos_correcao, segmentos_juros, [], date(2024, 3, 31), buscar)


def test_caso_6_parada_suspende_so_correcao():
    """Parada extraordinária em fevereiro suspende só a correção monetária
    — os juros daquele mês continuam incidindo sobre o saldo (congelado)."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    segmentos_juros = [JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), None, taxa_valor=Decimal("0.005"))]
    paradas = [ParadaExtraordinaria(date(2024, 2, 1), date(2024, 2, 29), suspende_correcao=True, suspende_juros=False)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, segmentos_juros, paradas, date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("1035.30")
    assert resultado.memoria[1].saldo_corrigido == resultado.memoria[0].saldo_corrigido  # congelado em fev
    assert resultado.memoria[1].juros_mes > 0  # juros continuou


def test_caso_7_parada_suspende_so_juros():
    """Parada extraordinária em fevereiro suspende só os juros — a correção
    monetária daquele mês continua normalmente."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    segmentos_juros = [JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), None, taxa_valor=Decimal("0.005"))]
    paradas = [ParadaExtraordinaria(date(2024, 2, 1), date(2024, 2, 29), suspende_correcao=False, suspende_juros=True)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, segmentos_juros, paradas, date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("1040.50")
    assert resultado.memoria[1].juros_mes == Decimal("0")
    assert resultado.memoria[1].saldo_corrigido > resultado.memoria[0].saldo_corrigido  # correção continuou


def test_caso_8_pagamento_parcial_no_meio_do_periodo():
    """Pagamento parcial em fevereiro abate o saldo antes da correção
    daquele mês; a linha do tempo continua sobre o saldo reduzido."""
    parcela = Parcela(
        vencimento=date(2024, 1, 1),
        valor_bruto=Decimal("1000"),
        pagamentos=(Pagamento(date(2024, 2, 15), Decimal("200")),),
    )
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("826.28")


def test_caso_9_pagamento_quita_o_saldo():
    """Pagamento maior que o saldo devedor quita a parcela — a linha do
    tempo para naquela competência e o valor final fica negativo (crédito
    a favor do devedor), sem ser truncado em zero silenciosamente."""
    parcela = Parcela(
        vencimento=date(2024, 1, 1),
        valor_bruto=Decimal("1000"),
        pagamentos=(Pagamento(date(2024, 2, 10), Decimal("1500")),),
    )
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 3, 31), buscar)

    assert resultado.valor_apurado == Decimal("-490.00")
    assert len(resultado.memoria) == 2  # jan normal, fev quitação — não chega a processar março
    assert resultado.memoria[-1].quitado is True


def test_caso_10a_prorata_no_inicio_do_periodo():
    """Vencimento no meio do mês (dia 16 de um mês de 30 dias) — a
    variação do índice deve ser proporcionalizada por 15/30 dias."""
    parcela = Parcela(vencimento=date(2024, 4, 16), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 4, 1), None)]
    buscar = criar_buscar_variacao({(Indice.IPCA, date(2024, 4, 1)): Decimal("0.02")})

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 4, 30), buscar)

    assert resultado.valor_apurado == Decimal("1010.00")


def test_caso_10b_prorata_no_fim_do_periodo():
    """Data do cálculo no meio do mês (dia 15 de um mês de 30 dias) — a
    variação do último mês deve ser proporcionalizada por 15/30 dias."""
    parcela = Parcela(vencimento=date(2024, 4, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 4, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 4, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 5, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 6, 1)): Decimal("0.02"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 6, 15), buscar)

    assert resultado.valor_apurado == Decimal("1030.30")


def test_caso_11_acessorio_sobre_total_liquido_das_parcelas():
    """Acessório (ex.: honorários de sucumbência) calculado como percentual
    do total já apurado de múltiplas parcelas, sem correção própria."""
    resultado_a = ResultadoCalculo(valor_apurado=Decimal("1000.00"), memoria=())
    resultado_b = ResultadoCalculo(valor_apurado=Decimal("500.00"), memoria=())
    total_parcelas = calcular_total_processo([resultado_a, resultado_b], [])

    acessorio = Acessorio(
        percentual=Decimal("0.10"),
        valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.TOTAL_LIQUIDO_PARCELAS,
        data_evento=None,
    )
    buscar = criar_buscar_variacao({})

    resultado_acessorio = calcular_acessorio(
        acessorio, total_parcelas, Decimal("0"), date(2024, 3, 31), [], [], [], buscar
    )

    assert total_parcelas == Decimal("1500.00")
    assert resultado_acessorio.valor_apurado == Decimal("150.00")


def test_caso_12_acessorio_com_data_evento_recebe_correcao_propria():
    """Acessório com data_evento preenchida passa pela mesma linha do
    tempo de correção do motor principal a partir daquela data."""
    total_parcelas = Decimal("1000.00")
    acessorio = Acessorio(
        percentual=Decimal("0.10"),
        valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.TOTAL_LIQUIDO_PARCELAS,
        data_evento=date(2024, 1, 1),
    )
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    resultado = calcular_acessorio(
        acessorio, total_parcelas, Decimal("0"), date(2024, 3, 31), segmentos_correcao, [], [], buscar
    )

    assert resultado.valor_apurado == Decimal("103.03")


def test_caso_13_dois_pagamentos_parciais_em_competencias_diferentes():
    """Dois pagamentos em meses diferentes — cada abatimento na sua data,
    saldo atualizado só sobre o remanescente entre um e outro."""
    parcela = Parcela(
        vencimento=date(2024, 1, 1),
        valor_bruto=Decimal("1000"),
        pagamentos=(
            Pagamento(date(2024, 2, 15), Decimal("300")),
            Pagamento(date(2024, 3, 10), Decimal("200")),
        ),
    )
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 4, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 4, 30), buscar)

    # 1000*1.01=1010 -300=710 *1.01=717.10 -200=517.10 *1.01=522.271 *1.01=527.49371
    assert resultado.valor_apurado == Decimal("527.49")
    assert resultado.memoria[1].saldo_inicio == Decimal("710")  # já líquido do 1º pagamento
    assert resultado.memoria[2].saldo_inicio == Decimal("517.10")  # já líquido do 2º pagamento


def test_caso_14_acessorio_523_com_saldo_remanescente_em_data_evento():
    """Multa/honorários do art. 523 CPC quando houve depósito parcial
    tempestivo: a base é o saldo das parcelas atualizado até `data_evento`
    (já líquido do depósito anterior a essa data) — não o total bruto,
    não o saldo na data final do cálculo."""
    parcela = Parcela(
        vencimento=date(2024, 1, 1),
        valor_bruto=Decimal("1000"),
        pagamentos=(Pagamento(date(2024, 1, 20), Decimal("400")),),
    )
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    data_evento = date(2024, 1, 31)  # fim do prazo de 15 dias do art. 523

    # O chamador (camada de serviço) roda calcular_parcela com hoje=data_evento
    # e soma os valor_apurado — é isso que calcular_acessorio recebe pronto.
    resultado_remanescente = calcular_parcela(parcela, segmentos_correcao, [], [], data_evento, buscar)
    assert resultado_remanescente.valor_apurado == Decimal("606.00")  # (1000-400)*1.01

    acessorio = Acessorio(
        percentual=Decimal("0.10"),
        valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.SALDO_REMANESCENTE_EM_DATA_EVENTO,
        data_evento=data_evento,
    )

    resultado = calcular_acessorio(
        acessorio,
        Decimal("0"),  # total_liquido_parcelas — irrelevante nesta base
        Decimal("0"),  # total_principal_sem_correcao — irrelevante nesta base
        date(2024, 3, 31),
        segmentos_correcao,
        [],
        [],
        buscar,
        total_saldo_remanescente_em_data_evento=resultado_remanescente.valor_apurado,
    )

    # base = 606.00 * 0.10 = 60.6000, depois corrige de 31/jan a 31/mar
    assert resultado.valor_apurado == Decimal("61.84")
    # não pode ser nem 10% do total bruto (1000*0.10=100, corrigido seria maior)
    # nem 10% do saldo já quitado na data final — só do remanescente em data_evento
    assert resultado.valor_apurado != (Decimal("1000") * Decimal("0.10")).quantize(Decimal("0.01"))


def test_caso_15_deflacao_permitida_aplica_variacao_negativa():
    """Campo 'Deflação (índices negativos)' — 'Com deflação' (padrão,
    permite_deflacao=True) deixa a variação negativa do índice reduzir o
    saldo normalmente."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None, permite_deflacao=True)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("-0.02"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 3, 31), buscar)

    # 1000*1.01=1010 *0.98=989.80 *1.01=999.698 -> arredonda 999.70
    assert resultado.valor_apurado == Decimal("999.70")


def test_caso_15b_sem_deflacao_zera_variacao_negativa():
    """'Sem deflação' (permite_deflacao=False) trata a variação negativa
    daquele mês como zero — protege o saldo de deflação."""
    parcela = Parcela(vencimento=date(2024, 1, 1), valor_bruto=Decimal("1000"))
    segmentos_correcao = [CorrecaoSegmento(Indice.IPCA, date(2024, 1, 1), None, permite_deflacao=False)]
    buscar = criar_buscar_variacao({
        (Indice.IPCA, date(2024, 1, 1)): Decimal("0.01"),
        (Indice.IPCA, date(2024, 2, 1)): Decimal("-0.02"),
        (Indice.IPCA, date(2024, 3, 1)): Decimal("0.01"),
    })

    resultado = calcular_parcela(parcela, segmentos_correcao, [], [], date(2024, 3, 31), buscar)

    # 1000*1.01=1010 (fev fica zerado, sem deflação) *1.01=1020.10
    assert resultado.valor_apurado == Decimal("1020.10")
    assert resultado.memoria[1].variacao_indice == Decimal(0)


def test_caso_16_contagem_juros_por_competencia_cobra_mes_cheio():
    """Campo 'Contagem Juros' — 'Por Competência' cobra o mês cheio de
    juros mesmo num mês parcial (vencimento no meio do mês), diferente do
    padrão 'Pró-rata' que proporcionaliza pelos dias decorridos."""
    parcela = Parcela(vencimento=date(2024, 4, 16), valor_bruto=Decimal("1000"))
    segmentos_juros = [
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 4, 1), None, taxa_valor=Decimal("0.01"))
    ]
    buscar = criar_buscar_variacao({})

    pro_rata = calcular_parcela(
        parcela, [], segmentos_juros, [], date(2024, 4, 30), buscar, contagem_juros=ContagemJuros.PRO_RATA
    )
    por_competencia = calcular_parcela(
        parcela, [], segmentos_juros, [], date(2024, 4, 30), buscar, contagem_juros=ContagemJuros.POR_COMPETENCIA
    )

    assert pro_rata.valor_apurado == Decimal("1005.00")  # 15/30 dias
    assert por_competencia.valor_apurado == Decimal("1010.00")  # mês cheio


def test_acessorio_saldo_remanescente_sem_data_evento_levanta_erro():
    """`data_evento` é obrigatória para essa base — seção 3.9/schema."""
    with pytest.raises(ValueError, match="data_evento"):
        Acessorio(
            percentual=Decimal("0.10"),
            valor_fixo=None,
            base_calculo=BaseCalculoAcessorio.SALDO_REMANESCENTE_EM_DATA_EVENTO,
            data_evento=None,
        )


def test_caso_17_acessorio_sobre_o_valor_da_causa():
    """Base 'Sobre o Valor da Causa' (paridade SOSCálculos, passo 3) —
    percentual incide sobre `Processo.valor_causa`, não sobre o total
    das parcelas nem sobre o principal sem correção."""
    acessorio = Acessorio(
        percentual=Decimal("0.10"),
        valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.VALOR_DA_CAUSA,
        data_evento=None,
    )
    buscar = criar_buscar_variacao({})

    resultado = calcular_acessorio(
        acessorio, Decimal("999999.99"), Decimal("999999.99"), date(2024, 3, 31), [], [], [], buscar,
        valor_causa=Decimal("50000.00"),
    )

    assert resultado.valor_apurado == Decimal("5000.00")


def test_caso_17c_pagamento_sem_art_354_cc_abate_principal_direto():
    """Padrão (aplicar_art_354_cc=False): pagamento reduz o principal
    diretamente, ignorando juros já vencidos — comportamento já
    documentado antes desta paridade."""
    parcela = Parcela(
        vencimento=date(2024, 1, 1),
        valor_bruto=Decimal("1000"),
        pagamentos=(Pagamento(date(2024, 4, 1), Decimal("50")),),
    )
    segmentos_juros = [
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), None, taxa_valor=Decimal("0.01"))
    ]
    buscar = criar_buscar_variacao({})

    resultado = calcular_parcela(
        parcela, [], segmentos_juros, [], date(2024, 4, 30), buscar, aplicar_art_354_cc=False
    )

    assert resultado.valor_apurado == Decimal("989.50")


def test_caso_17d_com_art_354_cc_abate_juros_vencidos_primeiro():
    """Art. 354 CC (aplicar_art_354_cc=True): o pagamento de R$50 abate
    primeiro os R$30 de juros já vencidos (jan+fev+mar, 10 cada) e só o
    excedente (R$20) reduz o principal — resultado diferente do modo
    padrão para o mesmo cenário."""
    parcela = Parcela(
        vencimento=date(2024, 1, 1),
        valor_bruto=Decimal("1000"),
        pagamentos=(Pagamento(date(2024, 4, 1), Decimal("50")),),
    )
    segmentos_juros = [
        JurosSegmento(TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL, date(2024, 1, 1), None, taxa_valor=Decimal("0.01"))
    ]
    buscar = criar_buscar_variacao({})

    resultado = calcular_parcela(
        parcela, [], segmentos_juros, [], date(2024, 4, 30), buscar, aplicar_art_354_cc=True
    )

    assert resultado.valor_apurado == Decimal("989.80")
    assert resultado.valor_apurado != Decimal("989.50")


def test_caso_18_multa_diaria_data_final_bate_com_calculo_real_soscalculos():
    """Multa 'Diária (Data final)' — caso de referência extraído de um
    PDF real gerado pelo SOSCálculos (R$10/dia de 01/01/2024 a
    01/03/2024 = 60 dias = R$600,00, sem correção/juros próprios)."""
    acessorio = Acessorio(
        percentual=None,
        valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO,
        data_evento=date(2024, 3, 1),
        valor_diario=Decimal("10.00"),
        data_inicio_acumulo=date(2024, 1, 1),
    )
    buscar = criar_buscar_variacao({})

    resultado = calcular_acessorio(
        acessorio, Decimal("0"), Decimal("0"), date(2026, 7, 29), [], [], [], buscar
    )

    assert resultado.valor_apurado == Decimal("600.00")


def test_caso_18b_valor_diario_exige_datas_de_acumulo():
    """valor_diario sem as datas de início/fim do acúmulo é inválido —
    fica ambíguo quantos dias contar."""
    with pytest.raises(ValueError, match="data_inicio_acumulo"):
        Acessorio(
            percentual=None,
            valor_fixo=None,
            base_calculo=BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO,
            data_evento=date(2024, 3, 1),
            valor_diario=Decimal("10.00"),
            data_inicio_acumulo=None,
        )


def test_caso_17b_acessorio_sobre_o_valor_da_causa_sem_valor_causa_levanta_erro():
    """Sem `valor_causa` preenchido no processo, calcular essa base deve
    falhar com uma mensagem clara em vez de um erro genérico."""
    acessorio = Acessorio(
        percentual=Decimal("0.10"),
        valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.VALOR_DA_CAUSA,
        data_evento=None,
    )
    buscar = criar_buscar_variacao({})

    with pytest.raises(ValueError, match="Valor da Causa"):
        calcular_acessorio(
            acessorio, Decimal("0"), Decimal("0"), date(2024, 3, 31), [], [], [], buscar, valor_causa=None
        )
