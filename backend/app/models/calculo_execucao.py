import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .base import TimestampMixin, UUIDPk
from .tipos import DecimalText

if TYPE_CHECKING:
    from .memoria_calculo import MemoriaCalculo
    from .processo import Processo


class CalculoExecucao(UUIDPk, TimestampMixin, Base):
    """Agrupa uma execução completa do motor (seção 2/8).

    Cada emissão de PDF (passo 4) cria uma linha aqui e persiste a
    `memoria_calculo` correspondente ANTES de renderizar — isso é o que
    permite reconstituir exatamente o PDF de uma liquidação já emitida,
    mesmo que a série de índice seja corrigida depois pelo BCB.
    """

    __tablename__ = "calculo_execucao"

    processo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data_calculo: Mapped[date] = mapped_column(Date, nullable=False)
    valor_total_apurado: Mapped[Decimal] = mapped_column(DecimalText(18, 2), nullable=False)
    # Hash/checksum do conteúdo do PDF emitido (seção 8) — preenchido no
    # momento da renderização, para provar depois que o documento não foi
    # alterado.
    hash_conteudo: Mapped[str | None] = mapped_column(String, nullable=True)

    processo: Mapped["Processo"] = relationship(back_populates="calculo_execucoes")
    memoria_linhas: Mapped[list["MemoriaCalculo"]] = relationship(
        back_populates="calculo_execucao", cascade="all, delete-orphan"
    )
