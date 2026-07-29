from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.engine.types import ContagemJuros

from .base import TimestampMixin, UUIDPk
from .tipos import DecimalText

if TYPE_CHECKING:
    from .acessorio import Acessorio
    from .calculo_execucao import CalculoExecucao
    from .deducao import Deducao
    from .parada import ParadaExtraordinaria
    from .parcela import Parcela
    from .segmento import CorrecaoSegmento, JurosSegmento


class Processo(UUIDPk, TimestampMixin, Base):
    __tablename__ = "processo"

    # Só requerente/requerido/data_calculo são obrigatórios — bate com o
    # passo 1 do SOSCálculos (seção 0/2): "Processo", "Contrato",
    # "Comarca", "Vara" e "Feito" lá são opcionais. O wizard permite
    # salvar rascunho incompleto.
    titulo_calculo: Mapped[str | None] = mapped_column(nullable=True)
    numero_processo: Mapped[str | None] = mapped_column(nullable=True)
    requerente: Mapped[str] = mapped_column(nullable=False)
    requerente_doc: Mapped[str | None] = mapped_column(nullable=True)
    requerido: Mapped[str] = mapped_column(nullable=False)
    requerido_doc: Mapped[str | None] = mapped_column(nullable=True)
    tribunal: Mapped[str | None] = mapped_column(nullable=True)
    comarca: Mapped[str | None] = mapped_column(nullable=True)
    vara: Mapped[str | None] = mapped_column(nullable=True)
    tipo_acao: Mapped[str | None] = mapped_column(nullable=True)
    # Campos "Contrato" e "Feito" do passo 1 (paridade SOSCálculos) — só
    # texto livre; "Feito" no SOSCálculos é um autocomplete cujo alvo de
    # busca não foi confirmado, então aqui é um campo de texto simples.
    contrato: Mapped[str | None] = mapped_column(nullable=True)
    feito: Mapped[str | None] = mapped_column(nullable=True)
    observacoes: Mapped[str | None] = mapped_column(nullable=True)
    data_calculo: Mapped[date] = mapped_column(nullable=False)
    # Base "Sobre o Valor da Causa" do passo 3 (paridade SOSCálculos) —
    # valor da petição inicial, distinto do total apurado das parcelas;
    # só texto/número informado pelo usuário, sem regra de cálculo aqui.
    valor_causa: Mapped[Decimal | None] = mapped_column(DecimalText(18, 2), nullable=True)

    # Checkboxes do passo 1.
    exibir_relatorio_detalhado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exibir_relatorio_correcao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # "Contagem Juros" (seção "Configurações de Juros Moratórios") — só
    # afeta a proporcionalização dos juros no motor (seção 3.7), nunca a
    # correção monetária.
    contagem_juros: Mapped[ContagemJuros] = mapped_column(
        Enum(ContagemJuros, name="contagem_juros"), nullable=False, default=ContagemJuros.PRO_RATA
    )

    # "Configurar Deduções" (Sim habilita o passo extra de Deduções,
    # seção 4) e "Aplicar Art. 354 do CC" (paridade SOSCálculos) — o
    # art. 354 do Código Civil determina que o pagamento se imputa
    # primeiro nos juros vencidos e só depois no capital; False (padrão)
    # mantém o comportamento já documentado (abate o principal direto).
    configura_deducoes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aplicar_art_354_cc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Datas-âncora usadas pelos dropdowns "Vencimento da C.M." / "Tipo
    # Vencimento Juros" (seção 0/2) para pré-preencher o data_inicio de um
    # segmento — "Do Vencimento" usa o vencimento da própria parcela e não
    # precisa de âncora aqui.
    data_citacao: Mapped[date | None] = mapped_column(nullable=True)
    data_distribuicao: Mapped[date | None] = mapped_column(nullable=True)
    data_sentenca: Mapped[date | None] = mapped_column(nullable=True)
    data_transito_julgado: Mapped[date | None] = mapped_column(nullable=True)
    data_publicacao: Mapped[date | None] = mapped_column(nullable=True)
    data_fixa: Mapped[date | None] = mapped_column(nullable=True)
    data_homologacao: Mapped[date | None] = mapped_column(nullable=True)
    data_aposentadoria: Mapped[date | None] = mapped_column(nullable=True)
    data_evento_padrao: Mapped[date | None] = mapped_column(nullable=True)

    parcelas: Mapped[list["Parcela"]] = relationship(
        back_populates="processo", cascade="all, delete-orphan"
    )
    acessorios: Mapped[list["Acessorio"]] = relationship(
        back_populates="processo", cascade="all, delete-orphan"
    )
    correcao_segmentos_default: Mapped[list["CorrecaoSegmento"]] = relationship(
        back_populates="processo",
        cascade="all, delete-orphan",
        primaryjoin="and_(Processo.id==CorrecaoSegmento.processo_id)",
    )
    juros_segmentos_default: Mapped[list["JurosSegmento"]] = relationship(
        back_populates="processo",
        cascade="all, delete-orphan",
        primaryjoin="and_(Processo.id==JurosSegmento.processo_id)",
    )
    calculo_execucoes: Mapped[list["CalculoExecucao"]] = relationship(
        back_populates="processo", cascade="all, delete-orphan"
    )
    paradas: Mapped[list["ParadaExtraordinaria"]] = relationship(
        back_populates="processo", cascade="all, delete-orphan"
    )
    deducoes: Mapped[list["Deducao"]] = relationship(
        back_populates="processo", cascade="all, delete-orphan"
    )
