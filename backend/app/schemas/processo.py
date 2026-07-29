from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.engine.types import ContagemJuros

from .segmento import CorrecaoSegmentoIn, CorrecaoSegmentoOut, JurosSegmentoIn, JurosSegmentoOut
from .tipos import DecimalStr


class ProcessoCreate(BaseModel):
    # Só requerente/requerido/data_calculo são obrigatórios (seção 0/2,
    # passo 1) — bate com o SOSCálculos: "Processo", "Contrato",
    # "Comarca", "Vara" e "Feito" são opcionais lá.
    requerente: str
    requerido: str
    data_calculo: date
    numero_processo: Optional[str] = None
    comarca: Optional[str] = None
    vara: Optional[str] = None
    contrato: Optional[str] = None
    feito: Optional[str] = None
    titulo_calculo: Optional[str] = None
    requerente_doc: Optional[str] = None
    requerido_doc: Optional[str] = None
    tribunal: Optional[str] = None
    tipo_acao: Optional[str] = None
    observacoes: Optional[str] = None
    exibir_relatorio_detalhado: bool = True
    exibir_relatorio_correcao: bool = False
    contagem_juros: ContagemJuros = ContagemJuros.PRO_RATA
    configura_deducoes: bool = False
    aplicar_art_354_cc: bool = False
    data_citacao: Optional[date] = None
    data_distribuicao: Optional[date] = None
    data_sentenca: Optional[date] = None
    data_transito_julgado: Optional[date] = None
    data_publicacao: Optional[date] = None
    data_fixa: Optional[date] = None
    data_homologacao: Optional[date] = None
    data_aposentadoria: Optional[date] = None
    data_evento_padrao: Optional[date] = None
    valor_causa: Optional[DecimalStr] = None
    correcao_segmentos_default: list[CorrecaoSegmentoIn] = []
    juros_segmentos_default: list[JurosSegmentoIn] = []


class ProcessoUpdate(ProcessoCreate):
    pass


class ProcessoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    numero_processo: Optional[str] = None
    requerente: str
    requerido: str
    data_calculo: date
    ultimo_total_apurado: Optional[DecimalStr] = None


class ProcessoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requerente: str
    requerido: str
    data_calculo: date
    numero_processo: Optional[str] = None
    comarca: Optional[str] = None
    vara: Optional[str] = None
    contrato: Optional[str] = None
    feito: Optional[str] = None
    titulo_calculo: Optional[str] = None
    requerente_doc: Optional[str] = None
    requerido_doc: Optional[str] = None
    tribunal: Optional[str] = None
    tipo_acao: Optional[str] = None
    observacoes: Optional[str] = None
    exibir_relatorio_detalhado: bool = True
    exibir_relatorio_correcao: bool = False
    contagem_juros: ContagemJuros = ContagemJuros.PRO_RATA
    configura_deducoes: bool = False
    aplicar_art_354_cc: bool = False
    data_citacao: Optional[date] = None
    data_distribuicao: Optional[date] = None
    data_sentenca: Optional[date] = None
    data_transito_julgado: Optional[date] = None
    data_publicacao: Optional[date] = None
    data_fixa: Optional[date] = None
    data_homologacao: Optional[date] = None
    data_aposentadoria: Optional[date] = None
    data_evento_padrao: Optional[date] = None
    valor_causa: Optional[DecimalStr] = None
    correcao_segmentos_default: list[CorrecaoSegmentoOut] = []
    juros_segmentos_default: list[JurosSegmentoOut] = []
