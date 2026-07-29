"""Enums específicos da camada de persistência.

Os enums que também têm significado no motor de cálculo (`Indice`,
`TipoTaxaJuros`, `BaseCalculoAcessorio`) NÃO são redefinidos aqui — são
importados de `app.engine.types` para manter uma única fonte de verdade
entre o schema do banco e o motor puro.
"""
from __future__ import annotations

from enum import Enum


class DonoTipo(str, Enum):
    PROCESSO_DEFAULT = "processo_default"
    PARCELA_OVERRIDE = "parcela_override"
    ACESSORIO_OVERRIDE = "acessorio_override"
    DEDUCAO_OVERRIDE = "deducao_override"


class FonteIndice(str, Enum):
    BCB_SGS = "bcb_sgs"
    IBGE = "ibge"
    MANUAL = "manual"


class TipoAcessorio(str, Enum):
    HONORARIOS_SUCUMBENCIA = "honorarios_sucumbencia"
    MULTA_523_CPC = "multa_523_cpc"
    HONORARIOS_523_CPC = "honorarios_523_cpc"
    HONORARIOS_CONTRATUAIS = "honorarios_contratuais"
    HONORARIOS_EXECUCAO = "honorarios_execucao"
    MULTA = "multa"
    CUSTAS_PROCESSUAIS = "custas_processuais"


class TipoPagamentoParcial(str, Enum):
    """Rótulo da dedução (seção 2/3.6) — não muda o algoritmo de
    abatimento no motor, só classifica a linha na memória/PDF."""

    PAGAMENTO = "pagamento"
    DEPOSITO_JUDICIAL = "deposito_judicial"
    COMPENSACAO = "compensacao"
    OUTRO = "outro"


class TipoDeducao(str, Enum):
    """Campo "Tipo" do passo "Deduções" (paridade SOSCálculos, só
    aparece quando `Processo.configura_deducoes` é True) — rótulo da
    dedução, sem efeito no motor além de classificar a linha."""

    ADJUDICACAO = "adjudicacao"
    ALVARA_LEVANTAMENTO = "alvara_levantamento"
    ALVARA_LEVANTAMENTO_ESTIMAR_TEMA_677 = "alvara_levantamento_estimar_tema_677"
    COMPENSACAO = "compensacao"
    COMPENSACAO_FINANCEIRO = "compensacao_financeiro"
    DEPOSITO_JUDICIAL = "deposito_judicial"
    DEPOSITO_JUDICIAL_TEMA_677 = "deposito_judicial_tema_677"
    PAGAMENTO = "pagamento"
    RECIBO = "recibo"


class TipoAtualizacaoDeducao(str, Enum):
    """Campo "Atualização" da dedução — decide qual data ancora a
    correção/juros próprios da dedução (seção 3.9, mesmo mecanismo de
    `data_evento` do Acessorio). DATA_LEVANTAMENTO e OUTRA_DATA usam a
    mesma âncora (`Deducao.data_atualizacao`, digitada manualmente) —
    o SOSCálculos os separa só como rótulos diferentes, sem uma origem
    própria pra "data do levantamento" no nosso modelo."""

    DATA_INICIAL = "data_inicial"
    DATA_CALCULO = "data_calculo"
    DATA_LEVANTAMENTO = "data_levantamento"
    OUTRA_DATA = "outra_data"


class TipoVencimento(str, Enum):
    """Campo "Vencimento da C.M." / "Tipo Vencimento Juros" do passo 1
    (paridade SOSCálculos). Só decide QUAL data-âncora do processo
    (`Processo.data_*`) pré-preenche o `data_inicio` do segmento no
    formulário — não tem efeito no motor de cálculo, que só enxerga a
    data já resolvida."""

    DO_VENCIMENTO = "do_vencimento"
    DA_CITACAO = "da_citacao"
    DA_DISTRIBUICAO = "da_distribuicao"
    DA_SENTENCA = "da_sentenca"
    DO_EVENTO = "do_evento"
    DO_TRANSITO_JULGADO = "do_transito_julgado"
    DA_PUBLICACAO = "da_publicacao"
    DA_DATA_FIXA = "da_data_fixa"
    DA_HOMOLOGACAO = "da_homologacao"
    DA_APOSENTADORIA = "da_aposentadoria"
