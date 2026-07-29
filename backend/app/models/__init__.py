"""Modelos ORM (seção 2 da especificação).

Importar tudo aqui garante que `Base.metadata` conheça todas as tabelas
antes do Alembic rodar autogenerate.
"""
from .acessorio import Acessorio
from .calculo_execucao import CalculoExecucao
from .deducao import Deducao
from .enums import (
    DonoTipo,
    FonteIndice,
    TipoAcessorio,
    TipoAtualizacaoDeducao,
    TipoDeducao,
    TipoPagamentoParcial,
)
from .indice_serie_valor import IndiceSerieValor
from .memoria_calculo import MemoriaCalculo
from .pagamento_parcial import PagamentoParcial
from .parada import ParadaExtraordinaria
from .parcela import Parcela
from .processo import Processo
from .salario_minimo_valor import SalarioMinimoValor
from .segmento import CorrecaoSegmento, JurosSegmento

__all__ = [
    "Acessorio",
    "CalculoExecucao",
    "Deducao",
    "DonoTipo",
    "FonteIndice",
    "TipoAcessorio",
    "TipoAtualizacaoDeducao",
    "TipoDeducao",
    "TipoPagamentoParcial",
    "IndiceSerieValor",
    "MemoriaCalculo",
    "PagamentoParcial",
    "ParadaExtraordinaria",
    "Parcela",
    "Processo",
    "SalarioMinimoValor",
    "CorrecaoSegmento",
    "JurosSegmento",
]
