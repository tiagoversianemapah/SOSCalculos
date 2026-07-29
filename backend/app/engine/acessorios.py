"""Cálculo de acessórios e do total do processo (seção 3.9)."""
from __future__ import annotations

from datetime import date
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
