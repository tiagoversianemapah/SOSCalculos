"""`salario_minimo_valor` — cadastro manual do valor ABSOLUTO (em R$) do
salário mínimo vigente a partir de uma competência (paridade SOSCálculos,
botão "Salário Mínimo" do passo 2).

Diferente de `indice_serie_valor` (que só guarda variação percentual mês
a mês, útil pra corrigir um valor já existente), esta tabela guarda o
valor absoluto — necessário pra gerar uma linha de crédito valendo "X%
do salário mínimo". Deliberadamente **não** populada automaticamente
nem com valores hardcoded no código: salário mínimo muda por decreto,
às vezes no meio do ano, e um valor errado aqui vai direto pra um
documento judicial — cadastro manual pelo usuário, com a fonte que ele
quiser (decreto, portaria).

Funciona como um "degrau": o valor cadastrado numa competência vale a
partir dali até a próxima competência cadastrada (não precisa cadastrar
todo mês, só quando muda) — ver `buscar_valor_vigente` em
`app/services/salario_minimo.py`.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

from .base import TimestampMixin, UUIDPk
from .tipos import DecimalText


class SalarioMinimoValor(UUIDPk, TimestampMixin, Base):
    __tablename__ = "salario_minimo_valor"
    __table_args__ = (UniqueConstraint("competencia", name="uq_salario_minimo_valor_competencia"),)

    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(DecimalText(18, 2), nullable=False)
