import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.engine.types import Indice

from .base import UUIDPk
from .enums import FonteIndice
from .tipos import DecimalText


class IndiceSerieValor(UUIDPk, Base):
    """Série histórica importada — append-only (seção 2).

    Nunca fazer UPDATE no valor de uma linha já usada em algum cálculo.
    Uma republicação retroativa do BCB cria uma nova linha e aponta
    `superseded_por` da linha antiga para ela — por isso a unicidade de
    (indice, competencia, tribunal_codigo) só vale entre linhas ainda
    ativas (`superseded_por IS NULL`); um índice único "cheio" rejeitaria
    a própria linha nova que substitui a antiga.

    `superseded_por` é UUID solto, sem FK: marcar a linha antiga como
    substituída e inserir a linha nova não pode ser feito na mesma
    transação com uma FK "pra frente" sem um dos dois passos violar,
    momentaneamente, o índice único parcial acima ou a própria FK (a
    nova linha ainda não existe quando a antiga precisaria apontar pra
    ela). O valor é sempre escrito por `atualizador.py`, nunca por
    entrada do usuário — o risco de ponteiro solto é interno e coberto
    por teste, não uma superfície de integridade que precise de reforço
    do banco.
    """

    __tablename__ = "indice_serie_valor"
    __table_args__ = (
        Index(
            "uq_indice_competencia_tribunal_ativo",
            "indice",
            "competencia",
            "tribunal_codigo",
            unique=True,
            sqlite_where=text("superseded_por IS NULL"),
            postgresql_where=text("superseded_por IS NULL"),
        ),
    )

    indice: Mapped[Indice] = mapped_column(Enum(Indice, name="indice"), nullable=False)
    # String vazia (não NULL) quando não aplicável — Postgres trata cada
    # NULL como distinto em constraints UNIQUE, o que quebraria o upsert
    # por (indice, competencia) da seção 5 para os índices não-tribunal.
    tribunal_codigo: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    variacao_percentual: Mapped[Decimal] = mapped_column(DecimalText(12, 8), nullable=False)
    fonte: Mapped[FonteIndice] = mapped_column(Enum(FonteIndice, name="fonte_indice"), nullable=False)
    importado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    superseded_por: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
