// Catálogo de presets do passo 1 — atalho de UI que pré-preenche o
// editor de segmentos (paridade com os dropdowns "Tabela Correção" /
// "Taxa de Juros" do SOSCálculos), sem inventar tabelas históricas
// compostas (ORTN/OTN/BTN, tabelas de Fazenda etc.) cuja regra exata de
// transição não foi confirmada — ver especificacao-tecnica-motor-
// -calculo-judicial.md, seção 11. Cada preset aqui só usa índices/taxas
// que o motor já suporta e, quando cita uma regra datada (ex.: Tema
// 1368/STJ), usa exatamente as datas do próprio rótulo — nada inferido.
// Qualquer configuração fora deste catálogo continua disponível editando
// os segmentos manualmente logo abaixo.
import type { CorrecaoSegmento, Indice, JurosSegmento } from "./types";

export interface PresetCorrecao {
  chave: string;
  categoria: string;
  rotulo: string;
  aplicar: (ordem: number) => CorrecaoSegmento;
}

export interface PresetJuros {
  chave: string;
  categoria: string;
  rotulo: string;
  aplicar: (ordem: number) => JurosSegmento;
}

function segmentoCorrecaoBase(ordem: number, indice: Indice): CorrecaoSegmento {
  return {
    ordem,
    indice,
    data_inicio: "",
    data_fim: null,
    fonte_criterio: "",
    vencimento_tipo: "do_vencimento",
    permite_deflacao: true,
    compor_com_selic: false,
  };
}

const INDICES_CATALOGO: { indice: Indice; rotulo: string }[] = [
  { indice: "ipca", rotulo: "IPCA" },
  { indice: "ipca_e", rotulo: "IPCA-E" },
  { indice: "inpc", rotulo: "INPC" },
  { indice: "igp_m", rotulo: "IGP-M" },
  { indice: "igp_di", rotulo: "IGP-DI" },
  { indice: "tr", rotulo: "TR" },
  { indice: "poupanca", rotulo: "Poupança" },
];

export const PRESETS_CORRECAO: PresetCorrecao[] = [
  ...INDICES_CATALOGO.map(({ indice, rotulo }) => ({
    chave: indice,
    categoria: "Índice único",
    rotulo,
    aplicar: (ordem: number) => segmentoCorrecaoBase(ordem, indice),
  })),
  {
    chave: "selic_substitutiva",
    categoria: "Selic",
    rotulo: "Selic (substitutiva — correção + juros embutidos)",
    aplicar: (ordem) => ({ ...segmentoCorrecaoBase(ordem, "sem_correcao"), compor_com_selic: true }),
  },
  {
    chave: "tema_1368_stj",
    categoria: "Selic",
    rotulo: "Tema 1368/STJ - Selic 01/2003 até 07/2024",
    aplicar: (ordem) => ({
      ...segmentoCorrecaoBase(ordem, "sem_correcao"),
      compor_com_selic: true,
      data_inicio: "2003-01-01",
      data_fim: "2024-07-31",
    }),
  },
  {
    chave: "sem_correcao",
    categoria: "Outros",
    rotulo: "Sem correção",
    aplicar: (ordem) => segmentoCorrecaoBase(ordem, "sem_correcao"),
  },
];

function segmentoJurosBase(ordem: number): Omit<JurosSegmento, "tipo_taxa" | "taxa_valor"> {
  return { ordem, data_inicio: "", data_fim: null, fonte_criterio: "", vencimento_tipo: "do_vencimento" };
}

export const PRESETS_JUROS: PresetJuros[] = [
  {
    chave: "taxa_legal",
    categoria: "Taxa legal",
    rotulo: "Taxa Legal (Selic conforme legislação vigente)",
    aplicar: (ordem) => ({ ...segmentoJurosBase(ordem), tipo_taxa: "taxa_legal", taxa_valor: null }),
  },
  {
    chave: "selic_substitutiva",
    categoria: "Taxa legal",
    rotulo: "Selic substitutiva (correção + juros)",
    aplicar: (ordem) => ({ ...segmentoJurosBase(ordem), tipo_taxa: "selic_substitutiva", taxa_valor: null }),
  },
  {
    chave: "0.005",
    categoria: "Percentual fixo",
    rotulo: "0,5% a.m. (6% a.a.)",
    aplicar: (ordem) => ({ ...segmentoJurosBase(ordem), tipo_taxa: "percentual_fixo_mensal", taxa_valor: "0.005" }),
  },
  {
    chave: "0.01",
    categoria: "Percentual fixo",
    rotulo: "1% a.m. (12% a.a.)",
    aplicar: (ordem) => ({ ...segmentoJurosBase(ordem), tipo_taxa: "percentual_fixo_mensal", taxa_valor: "0.01" }),
  },
];
