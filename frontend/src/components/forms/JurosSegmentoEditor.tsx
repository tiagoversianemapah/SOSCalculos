// Editor de lista ordenada de segmentos de juros moratórios —
// reutilizado no passo 1 (default) e no passo 2 (override), seção 6.2.
// "Tipo Vencimento Juros" replica o campo equivalente do SOSCálculos
// (paridade, seção 0/2).
import type { JurosSegmento, TipoTaxaJuros, TipoVencimento } from "../../lib/types";
import { TIPOS_TAXA_JUROS, TIPOS_VENCIMENTO } from "../../lib/types";

interface Props {
  segmentos: JurosSegmento[];
  onChange: (segmentos: JurosSegmento[]) => void;
  datasAncora?: Partial<Record<TipoVencimento, string | null | undefined>>;
}

function novoSegmento(ordem: number): JurosSegmento {
  return {
    ordem,
    tipo_taxa: "percentual_fixo_mensal",
    taxa_valor: "",
    data_inicio: "",
    data_fim: null,
    fonte_criterio: "",
    vencimento_tipo: "do_vencimento",
  };
}

export function JurosSegmentoEditor({ segmentos, onChange, datasAncora }: Props) {
  const atualizar = (indice: number, campo: keyof JurosSegmento, valor: unknown) => {
    onChange(segmentos.map((s, i) => (i === indice ? { ...s, [campo]: valor } : s)));
  };

  const trocarVencimentoTipo = (indice: number, tipo: TipoVencimento) => {
    const ancora = tipo === "do_vencimento" ? undefined : datasAncora?.[tipo];
    const copia = segmentos.map((s, i) =>
      i === indice ? { ...s, vencimento_tipo: tipo, ...(ancora ? { data_inicio: ancora } : {}) } : s
    );
    onChange(copia);
  };

  const remover = (indice: number) => {
    onChange(segmentos.filter((_, i) => i !== indice).map((s, i) => ({ ...s, ordem: i + 1 })));
  };

  const adicionar = () => onChange([...segmentos, novoSegmento(segmentos.length + 1)]);

  return (
    <div className="segmento-editor">
      <h4>Juros moratórios</h4>
      {segmentos.length === 0 && <p className="texto-auxiliar">Nenhum segmento — sem juros.</p>}
      {segmentos.map((segmento, i) => (
        <div className="segmento-bloco" key={i}>
          <div className="segmento-linha">
            <select
              value={segmento.tipo_taxa}
              onChange={(e) => atualizar(i, "tipo_taxa", e.target.value as TipoTaxaJuros)}
            >
              {TIPOS_TAXA_JUROS.map((opcao) => (
                <option key={opcao.value} value={opcao.value}>
                  {opcao.label}
                </option>
              ))}
            </select>
            {segmento.tipo_taxa === "percentual_fixo_mensal" && (
              <input
                placeholder="ex.: 0.01 = 1% a.m."
                value={segmento.taxa_valor ?? ""}
                onChange={(e) => atualizar(i, "taxa_valor", e.target.value)}
              />
            )}
            <input
              type="date"
              value={segmento.data_inicio}
              onChange={(e) => atualizar(i, "data_inicio", e.target.value)}
            />
            <span>até</span>
            <input
              type="date"
              value={segmento.data_fim ?? ""}
              placeholder="data do cálculo"
              onChange={(e) => atualizar(i, "data_fim", e.target.value || null)}
            />
            <input
              placeholder="fonte do critério"
              value={segmento.fonte_criterio ?? ""}
              onChange={(e) => atualizar(i, "fonte_criterio", e.target.value)}
            />
            <button type="button" onClick={() => remover(i)} aria-label="Remover segmento">
              ✕
            </button>
          </div>
          <div className="segmento-linha segmento-linha-config">
            <label>
              Tipo Vencimento Juros
              <select
                value={segmento.vencimento_tipo}
                onChange={(e) => trocarVencimentoTipo(i, e.target.value as TipoVencimento)}
              >
                {TIPOS_VENCIMENTO.map((opcao) => (
                  <option key={opcao.value} value={opcao.value}>
                    {opcao.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      ))}
      <button type="button" onClick={adicionar}>
        + adicionar taxa de juros
      </button>
    </div>
  );
}
