"""Mapeamento índice → série do BCB SGS (seção 5).

Só ficam aqui os índices cuja série do BCB SGS já foi verificada. Os
demais índices do enum `Indice` (IGP-DI, Selic Composta, TBF, TLP,
Salário Mínimo, tabela de tribunal, Pis/Pasep) não têm código mapeado
de propósito — a seção 5 já prevê fluxo manual (import de planilha)
pra eles; `atualizar_indice` recusa (`ValueError`) com mensagem clara
em vez de arriscar um código não confirmado.

**TR (226) e Poupança (195) não são séries mensais simples:** são
publicadas diariamente, cada linha com `data`/`dataFim` representando a
taxa da janela de 30 dias a partir daquele dia (ex.: a linha de
02/01/2020 vale para 02/01→02/02/2020) — não uma taxa diária simples
nem já a taxa do mês calendário. A convenção adotada (seção 5): usar
só a linha cujo `data` cai no **dia 1º do mês** — essa linha já
representa exatamente a taxa calendário (dia 1º ao dia 1º seguinte),
sem precisar compor nada.
"""
from __future__ import annotations

from app.engine.types import Indice

CODIGO_SGS: dict[Indice, int] = {
    Indice.IPCA: 433,
    Indice.INPC: 188,
    Indice.IGP_M: 189,
    Indice.SELIC_SIMPLES: 4390,  # Selic acumulada no mês, já em % — uma linha por mês
    Indice.TR: 226,  # diária por aniversário — ver SERIES_DIARIA_ANIVERSARIO
    Indice.POUPANCA: 195,  # idem TR
    Indice.PTAX: 1,  # cotação diária simples, sem campo dataFim
}

# Séries cujo valor publicado já é a variação percentual do próprio mês
# (dividir por 100 vira a fração usada pelo motor) — uma linha por
# competência, sem campo `dataFim`.
SERIES_JA_PERCENTUAL: frozenset[Indice] = frozenset(
    {Indice.IPCA, Indice.INPC, Indice.IGP_M, Indice.SELIC_SIMPLES}
)

# Séries diárias por "aniversário" (TR, Poupança — ver docstring do
# módulo): só a linha cujo `data` é dia 1º do mês representa a taxa
# calendário; as demais linhas do mês são descartadas. O valor dessa
# linha já é percentual (dividir por 100), igual a SERIES_JA_PERCENTUAL.
SERIES_DIARIA_ANIVERSARIO: frozenset[Indice] = frozenset({Indice.TR, Indice.POUPANCA})

# Séries cujo valor publicado é um nível absoluto (ex.: cotação PTAX),
# publicado em granularidade diária — a variação mensal precisa ser
# calculada a partir do último valor de cada mês (ver atualizador.py).
SERIES_NIVEL_ABSOLUTO: frozenset[Indice] = frozenset({Indice.PTAX})
