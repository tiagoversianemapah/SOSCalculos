// Rótulos legíveis para os dropdowns "Correção Monetária" / "Juros
// Moratórios" do passo 2 (paridade SOSCálculos) — reduz a lista de
// segmentos default do processo (passo 1) numa única string, do mesmo
// jeito que o SOSCálculos nomeia a tabela composta no dropdown por
// linha (ex.: "TJGO até 08/2024 e IPCA (Lei nº 14.905/24) após").
import { formatarCompetencia } from "./format";
import type { CorrecaoSegmento, JurosSegmento } from "./types";
import { INDICES } from "./types";

function nomeIndice(indice: string): string {
  return INDICES.find((i) => i.value === indice)?.label ?? indice;
}

export function rotularCorrecaoDefault(segmentos: CorrecaoSegmento[]): string {
  if (segmentos.length === 0) return "Correção do processo (nenhuma tabela configurada)";
  const ordenados = [...segmentos].slice().sort((a, b) => a.ordem - b.ordem);
  return ordenados
    .map((s, i) => {
      const nome = s.compor_com_selic ? "Selic (substitutiva)" : nomeIndice(s.indice);
      const ultimo = i === ordenados.length - 1;
      if (!ultimo && s.data_fim) return `${nome} até ${formatarCompetencia(s.data_fim)}`;
      if (ultimo && ordenados.length > 1) return `${nome} após`;
      return nome;
    })
    .join(" e ");
}

export function rotularJurosDefault(segmentos: JurosSegmento[]): string {
  if (segmentos.length === 0) return "Juros do processo (nenhuma taxa configurada)";
  const ordenados = [...segmentos].slice().sort((a, b) => a.ordem - b.ordem);
  return ordenados
    .map((s, i) => {
      let nome: string;
      if (s.tipo_taxa === "percentual_fixo_mensal" && s.taxa_valor) {
        const mensal = Number(s.taxa_valor) * 100;
        const anual = (Math.pow(1 + Number(s.taxa_valor), 12) - 1) * 100;
        nome = `${mensal.toLocaleString("pt-BR")}% a.m. (${anual.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% a.a.)`;
      } else if (s.tipo_taxa === "taxa_legal") {
        nome = "Taxa Legal";
      } else {
        nome = "Selic substitutiva";
      }
      const ultimo = i === ordenados.length - 1;
      if (!ultimo && s.data_fim) return `${nome} até ${formatarCompetencia(s.data_fim)}`;
      if (ultimo && ordenados.length > 1) return `${nome} após`;
      return nome;
    })
    .join(", ");
}
