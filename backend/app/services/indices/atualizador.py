"""Orquestra a atualização de `indice_serie_valor` (seção 5).

Detecta a última competência já gravada por índice, busca só o delta
faltante e grava via upsert em código de aplicação (nunca `INSERT OR
REPLACE` — invariante 12.1.4): se o valor mudar (BCB republicou um mês
retroativo), cria uma linha nova e aponta a antiga para ela via
`superseded_por`; nunca faz UPDATE no valor de uma linha existente.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.types import Indice
from app.models.enums import FonteIndice
from app.models.indice_serie_valor import IndiceSerieValor

from .bcb_sgs import IndiceOfflineError, buscar_serie
from .mapeamento import CODIGO_SGS, SERIES_DIARIA_ANIVERSARIO, SERIES_NIVEL_ABSOLUTO

BuscarSerie = Callable[[int, date, date], list[tuple[date, Decimal]]]

INICIO_SERIE_PADRAO = date(2000, 1, 1)


def _primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)


def _proximo_mes(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


def _mes_anterior(d: date) -> date:
    if d.month == 1:
        return d.replace(year=d.year - 1, month=12, day=1)
    return d.replace(month=d.month - 1, day=1)


def _proxima_competencia_a_buscar(db: Session, indice: Indice) -> date:
    ultima = db.execute(
        select(IndiceSerieValor.competencia)
        .where(
            IndiceSerieValor.indice == indice,
            IndiceSerieValor.tribunal_codigo == "",
            IndiceSerieValor.superseded_por.is_(None),
        )
        .order_by(IndiceSerieValor.competencia.desc())
        .limit(1)
    ).scalar_one_or_none()
    if ultima is None:
        return INICIO_SERIE_PADRAO
    return _proximo_mes(ultima)


def _valor_atual(db: Session, indice: Indice, competencia: date) -> IndiceSerieValor | None:
    return db.execute(
        select(IndiceSerieValor).where(
            IndiceSerieValor.indice == indice,
            IndiceSerieValor.competencia == competencia,
            IndiceSerieValor.tribunal_codigo == "",
            IndiceSerieValor.superseded_por.is_(None),
        )
    ).scalar_one_or_none()


def _upsert(db: Session, indice: Indice, competencia: date, variacao: Decimal, fonte: FonteIndice) -> bool:
    """Grava `variacao` para (indice, competencia). Devolve True se algo foi gravado/alterado.

    Quando já existe uma linha ativa com outro valor, a linha antiga
    precisa ser marcada como substituída ANTES de inserir a nova — o
    índice único parcial (seção 2/modelo) só permite uma linha ativa por
    (indice, competencia, tribunal_codigo), então inserir a nova antes
    ainda deixaria as duas ativas ao mesmo tempo e violaria o índice.
    """
    existente = _valor_atual(db, indice, competencia)
    if existente is not None:
        if existente.variacao_percentual == variacao:
            return False
        novo_id = uuid.uuid4()
        existente.superseded_por = novo_id
        db.flush()
        db.add(
            IndiceSerieValor(
                id=novo_id, indice=indice, competencia=competencia, variacao_percentual=variacao, fonte=fonte
            )
        )
        return True
    db.add(IndiceSerieValor(indice=indice, competencia=competencia, variacao_percentual=variacao, fonte=fonte))
    return True


def _reduzir_para_ultimo_valor_por_mes(pontos: list[tuple[date, Decimal]]) -> dict[date, Decimal]:
    por_mes: dict[date, Decimal] = {}
    for d, v in sorted(pontos):
        por_mes[_primeiro_dia_mes(d)] = v
    return por_mes


def atualizar_indice(
    db: Session,
    indice: Indice,
    hoje: date,
    buscar_serie_fn: BuscarSerie = buscar_serie,
) -> int:
    """Busca e grava o delta faltante de `indice` até a competência de `hoje`.

    Devolve quantas competências foram gravadas/alteradas. Levanta
    `IndiceOfflineError` se a rede falhar — o chamador decide como tratar
    (seção 5: nunca travar o app por causa disso).
    """
    codigo = CODIGO_SGS.get(indice)
    if codigo is None:
        raise ValueError(
            f"Índice {indice.value} não tem série do BCB SGS mapeada — "
            "atualização é manual (import de planilha, seção 5)"
        )

    inicio = _proxima_competencia_a_buscar(db, indice)
    fim = _primeiro_dia_mes(hoje)
    if inicio > fim:
        return 0

    eh_nivel_absoluto = indice in SERIES_NIVEL_ABSOLUTO
    busca_desde = _mes_anterior(inicio) if eh_nivel_absoluto else inicio

    pontos = buscar_serie_fn(codigo, busca_desde, fim)
    if not pontos:
        return 0

    if indice in SERIES_DIARIA_ANIVERSARIO:
        # TR/Poupança: só a linha do dia 1º do mês representa a taxa
        # calendário (ver docstring de mapeamento.py) — descarta o resto.
        pontos = [(d, v) for d, v in pontos if d.day == 1]

    gravados = 0
    if eh_nivel_absoluto:
        por_mes = _reduzir_para_ultimo_valor_por_mes(pontos)
        competencias = sorted(por_mes)
        for anterior, atual in zip(competencias, competencias[1:]):
            if atual < inicio:
                continue
            variacao = (por_mes[atual] - por_mes[anterior]) / por_mes[anterior]
            if _upsert(db, indice, atual, variacao, FonteIndice.BCB_SGS):
                gravados += 1
    else:
        for d, v in pontos:
            competencia = _primeiro_dia_mes(d)
            if competencia < inicio:
                continue
            variacao = v / Decimal(100)
            if _upsert(db, indice, competencia, variacao, FonteIndice.BCB_SGS):
                gravados += 1

    db.commit()
    return gravados


def atualizar_todos(
    db: Session, hoje: date, buscar_serie_fn: BuscarSerie = buscar_serie
) -> dict[Indice, int | str]:
    """Roda `atualizar_indice` para cada índice mapeado.

    Uma falha de rede num índice não aborta os outros — cada um é
    tentado independentemente; falha vira `"offline"` no resultado
    (seção 5: sem internet é um aviso não-bloqueante, nunca um erro fatal).
    """
    resultado: dict[Indice, int | str] = {}
    for indice in CODIGO_SGS:
        try:
            resultado[indice] = atualizar_indice(db, indice, hoje, buscar_serie_fn)
        except IndiceOfflineError:
            resultado[indice] = "offline"
    return resultado
