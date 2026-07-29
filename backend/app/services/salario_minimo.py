"""Busca do valor absoluto do salário mínimo vigente numa competência
(paridade SOSCálculos, botão "Salário Mínimo" do passo 2) — cadastro
manual, ver `app/models/salario_minimo_valor.py` para a justificativa de
não automatizar nem hardcodar isso no código.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.salario_minimo_valor import SalarioMinimoValor


def buscar_valor_vigente(db: Session, competencia: date) -> Decimal | None:
    """Valor cadastrado mais recente com `competencia <= alvo` — o valor
    vale como um "degrau" até o próximo cadastro (salário mínimo não
    muda todo mês). Devolve None se não houver nenhum cadastro anterior
    ou igual à competência pedida — o chamador decide como reportar isso
    (nunca assumir zero nem extrapolar um valor)."""
    return db.execute(
        select(SalarioMinimoValor.valor)
        .where(SalarioMinimoValor.competencia <= competencia)
        .order_by(SalarioMinimoValor.competencia.desc())
        .limit(1)
    ).scalar_one_or_none()
