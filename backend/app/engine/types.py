"""Value objects e enums do motor de cálculo.

Ver especificacao-tecnica-motor-calculo-judicial.md, seção 2 e 3, para o
significado jurídico de cada campo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional


class Indice(str, Enum):
    IPCA = "ipca"
    IPCA_E = "ipca_e"
    INPC = "inpc"
    IGP_M = "igp_m"
    IGP_DI = "igp_di"
    SELIC_SIMPLES = "selic_simples"
    SELIC_COMPOSTA = "selic_composta"
    TR = "tr"
    TBF = "tbf"
    TLP = "tlp"
    POUPANCA = "poupanca"
    PTAX = "ptax"
    SALARIO_MINIMO = "salario_minimo"
    TRIBUNAL = "tribunal"
    PIS_PASEP = "pis_pasep"
    SEM_CORRECAO = "sem_correcao"


class TipoTaxaJuros(str, Enum):
    PERCENTUAL_FIXO_MENSAL = "percentual_fixo_mensal"
    TAXA_LEGAL = "taxa_legal"
    SELIC_SUBSTITUTIVA = "selic_substitutiva"


class ContagemJuros(str, Enum):
    """Modo de contagem dos juros moratórios (campo "Contagem Juros" do
    passo 1, paridade SOSCálculos). PRO_RATA (padrão) conta os dias
    efetivamente decorridos no primeiro/último mês (seção 3.7);
    POR_COMPETENCIA cobra sempre o mês cheio, mesmo nos meses parciais —
    só afeta juros, nunca a correção monetária."""

    PRO_RATA = "pro_rata"
    POR_COMPETENCIA = "por_competencia"


class BaseCalculoAcessorio(str, Enum):
    TOTAL_LIQUIDO_PARCELAS = "total_liquido_parcelas"
    VALOR_PRINCIPAL_SEM_CORRECAO = "valor_principal_sem_correcao"
    VALOR_FIXO_ABSOLUTO = "valor_fixo_absoluto"
    # Base "Sobre o Valor da Causa" (paridade SOSCálculos) — percentual
    # sobre `Processo.valor_causa`, informado pelo usuário no passo 1/3;
    # não é derivado do cálculo das parcelas.
    VALOR_DA_CAUSA = "valor_da_causa"
    # Base do art. 523 CPC quando houve depósito parcial tempestivo
    # (seção 3.9): total das parcelas atualizado só até `data_evento`,
    # já líquido das deduções anteriores a essa data — não o total geral
    # nem o saldo na data do cálculo.
    SALDO_REMANESCENTE_EM_DATA_EVENTO = "saldo_remanescente_em_data_evento"


# Dado um índice e uma competência (dia 1 do mês), devolve a variação
# percentual daquele mês como fração (ex.: Decimal("0.00437") = 0,437%).
# Implementado pela camada de serviço (consulta indice_serie_valor no
# banco) — o motor nunca acessa o banco diretamente.
BuscarVariacao = Callable[[Indice, date], Decimal]


@dataclass(frozen=True)
class CorrecaoSegmento:
    indice: Indice
    data_inicio: date
    data_fim: Optional[date] = None  # None = "até a data do cálculo"
    # Campo "Deflação (índices negativos)" do passo 1 (paridade
    # SOSCálculos). True (padrão, "Com deflação") = variação negativa do
    # índice reduz o saldo normalmente. False ("Sem deflação") = variação
    # negativa vira zero naquele mês — protege o saldo de deflação.
    permite_deflacao: bool = True


@dataclass(frozen=True)
class JurosSegmento:
    tipo_taxa: TipoTaxaJuros
    data_inicio: date
    data_fim: Optional[date] = None
    # Fração mensal, só obrigatório quando tipo_taxa = PERCENTUAL_FIXO_MENSAL
    # (ex.: Decimal("0.005") = 0,5% ao mês).
    taxa_valor: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if self.tipo_taxa is TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL and self.taxa_valor is None:
            raise ValueError(
                "taxa_valor é obrigatório quando tipo_taxa = PERCENTUAL_FIXO_MENSAL"
            )


@dataclass(frozen=True)
class ParadaExtraordinaria:
    data_inicio: date
    data_fim: date
    suspende_correcao: bool = True
    suspende_juros: bool = True
    motivo: str = ""

    def __post_init__(self) -> None:
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio em uma parada")


@dataclass(frozen=True)
class Pagamento:
    data: date
    valor: Decimal


@dataclass(frozen=True)
class Parcela:
    vencimento: date
    valor_bruto: Decimal
    pagamentos: tuple[Pagamento, ...] = ()


@dataclass(frozen=True)
class Acessorio:
    percentual: Optional[Decimal]
    valor_fixo: Optional[Decimal]
    base_calculo: BaseCalculoAcessorio
    data_evento: Optional[date] = None
    # Multa "Diária (Data final)" do passo 3 (paridade SOSCálculos,
    # confirmado com um cálculo real: total = valor_diario × dias
    # corridos entre data_inicio_acumulo e data_evento, sem +1 — ex.:
    # 01/01/2024 a 01/03/2024 = 60 dias). Quando preenchido, substitui
    # `valor_fixo` no cálculo da base (mutuamente exclusivos).
    valor_diario: Optional[Decimal] = None
    data_inicio_acumulo: Optional[date] = None
    # Multa "Diária (Competência)" — confirmado com cálculo real: em vez
    # de um valor único ancorado na Data Fim, quebra em uma sub-linha por
    # mês civil (dias daquele mês × valor_diario), cada uma corrigida a
    # partir do 1º dia daquele mês até hoje (ver acessorios.py). Só tem
    # efeito quando valor_diario está preenchido.
    diaria_por_competencia: bool = False
    # Multa "Mensal" — confirmado com cálculo real: um valor fixo
    # lançado uma vez por mês vencido entre data_inicio_acumulo e
    # data_evento (marcos no mesmo dia-do-mês de data_inicio_acumulo,
    # começando no mês seguinte, até data_evento inclusive — ver
    # `_marcos_mensais` em acessorios.py), cada lançamento corrigido a
    # partir da sua própria data até hoje. Mutuamente exclusivo com
    # valor_diario/valor_fixo.
    valor_mensal: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if self.valor_diario is not None:
            if self.base_calculo is not BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
                raise ValueError(
                    "valor_diario só se aplica quando base_calculo = VALOR_FIXO_ABSOLUTO"
                )
            if self.data_inicio_acumulo is None or self.data_evento is None:
                raise ValueError(
                    "data_inicio_acumulo e data_evento são obrigatórias quando valor_diario "
                    "é informado (multa Diária — Data Início e Data Fim do acúmulo)"
                )
        elif self.valor_mensal is not None:
            if self.base_calculo is not BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
                raise ValueError(
                    "valor_mensal só se aplica quando base_calculo = VALOR_FIXO_ABSOLUTO"
                )
            if self.data_inicio_acumulo is None or self.data_evento is None:
                raise ValueError(
                    "data_inicio_acumulo e data_evento são obrigatórias quando valor_mensal "
                    "é informado (multa Mensal — Data Início e Data Fim do acúmulo)"
                )
        elif self.base_calculo is BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
            if self.valor_fixo is None:
                raise ValueError(
                    "valor_fixo é obrigatório quando base_calculo = VALOR_FIXO_ABSOLUTO "
                    "(a menos que valor_diario esteja preenchido)"
                )
        elif self.percentual is None:
            raise ValueError(
                "percentual é obrigatório quando base_calculo != VALOR_FIXO_ABSOLUTO"
            )
        if (
            self.base_calculo is BaseCalculoAcessorio.SALDO_REMANESCENTE_EM_DATA_EVENTO
            and self.data_evento is None
        ):
            raise ValueError(
                "data_evento é obrigatória quando base_calculo = SALDO_REMANESCENTE_EM_DATA_EVENTO"
            )


@dataclass(frozen=True)
class LinhaMemoria:
    """Uma linha da memória de cálculo (uma competência). Nada aqui é
    arredondado — arredondamento só acontece na exibição/PDF e no
    valor_apurado final (ver ResultadoCalculo)."""

    competencia: date
    saldo_inicio: Decimal
    indice: Optional[Indice]
    variacao_indice: Decimal
    saldo_corrigido: Decimal
    tipo_taxa_juros: Optional[TipoTaxaJuros]
    taxa_juros_mensal: Decimal
    juros_mes: Decimal
    saldo_final: Decimal
    parada_ativa: bool
    quitado: bool = False


@dataclass(frozen=True)
class ResultadoCalculo:
    valor_apurado: Decimal
    memoria: tuple[LinhaMemoria, ...]
