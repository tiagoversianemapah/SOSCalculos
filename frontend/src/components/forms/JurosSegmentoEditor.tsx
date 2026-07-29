// Editor de lista ordenada de segmentos de juros moratórios —
// reutilizado no passo 1 (default) e no passo 2 (override), seção 6.2.
// "Tipo Vencimento Juros" replica o campo equivalente do SOSCálculos
// (paridade, seção 0/2).
import type { JurosSegmento, TipoTaxaJuros, TipoVencimento } from "../../lib/types";
import { TIPOS_TAXA_JUROS, TIPOS_VENCIMENTO } from "../../lib/types";
import { Campo, VALIDACAO_INERTE, obrigatorio, type RegraCampo, type Validacao } from "../../lib/validacao";

interface Props {
  segmentos: JurosSegmento[];
  onChange: (segmentos: JurosSegmento[]) => void;
  datasAncora?: Partial<Record<TipoVencimento, string | null | undefined>>;
  // Validação por campo (ver lib/validacao.tsx).
  validacao?: Validacao;
  prefixo?: string;
}

/** Regras dos campos deste editor — junto do JSX para não saírem de
 * sincronia. `revelar` abre a seção que contém o editor quando recolhido. */
export function regrasJuros(
  prefixo: string,
  segmentos: JurosSegmento[],
  revelar?: () => void
): RegraCampo[] {
  const regras: RegraCampo[] = [];
  segmentos.forEach((segmento, i) => {
    regras.push(obrigatorio(`${prefixo}${i}.data_inicio`, segmento.data_inicio, "A data inicial", revelar));
    // Campo condicional: a taxa só aparece (e só faz sentido) no
    // percentual fixo — taxa legal e Selic substitutiva vêm da tabela.
    if (segmento.tipo_taxa === "percentual_fixo_mensal") {
      regras.push({
        nome: `${prefixo}${i}.taxa_valor`,
        valido: Boolean(segmento.taxa_valor && segmento.taxa_valor.trim() && Number(segmento.taxa_valor) > 0),
        mensagem: "Informe a taxa mensal (ex.: 0.01 = 1% a.m.).",
        revelar,
      });
    }
    if (segmento.data_inicio && segmento.data_fim && segmento.data_fim < segmento.data_inicio) {
      regras.push({
        nome: `${prefixo}${i}.data_fim`,
        valido: false,
        mensagem: "A data final não pode ser anterior à inicial.",
        revelar,
      });
    }
  });
  return regras;
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

export function JurosSegmentoEditor({
  segmentos,
  onChange,
  datasAncora,
  validacao = VALIDACAO_INERTE,
  prefixo = "juros.",
}: Props) {
  const atualizar = (indice: number, campo: keyof JurosSegmento, valor: unknown) => {
    onChange(segmentos.map((s, i) => (i === indice ? { ...s, [campo]: valor } : s)));
  };

  // Sair do "percentual fixo mensal" esconde o campo de taxa — o valor
  // que ficou nele tem que ir junto. Uma string vazia esquecida aqui é
  // recusada pelo backend (DecimalStr não aceita "") com um 422 que não
  // diz qual campo é; `null` é o "sem taxa própria" que ele espera.
  const trocarTipoTaxa = (indice: number, tipo: TipoTaxaJuros) => {
    onChange(
      segmentos.map((s, i) =>
        i === indice
          ? { ...s, tipo_taxa: tipo, taxa_valor: tipo === "percentual_fixo_mensal" ? s.taxa_valor : null }
          : s
      )
    );
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
              onChange={(e) => trocarTipoTaxa(i, e.target.value as TipoTaxaJuros)}
            >
              {TIPOS_TAXA_JUROS.map((opcao) => (
                <option key={opcao.value} value={opcao.value}>
                  {opcao.label}
                </option>
              ))}
            </select>
            {segmento.tipo_taxa === "percentual_fixo_mensal" && (
              <Campo nome={`${prefixo}${i}.taxa_valor`} validacao={validacao} como="div">
                <input
                  placeholder="ex.: 0.01 = 1% a.m."
                  value={segmento.taxa_valor ?? ""}
                  onChange={(e) => atualizar(i, "taxa_valor", e.target.value)}
                />
              </Campo>
            )}
            <Campo nome={`${prefixo}${i}.data_inicio`} validacao={validacao} como="div">
              <input
                type="date"
                value={segmento.data_inicio}
                onChange={(e) => atualizar(i, "data_inicio", e.target.value)}
              />
            </Campo>
            <span>até</span>
            <Campo nome={`${prefixo}${i}.data_fim`} validacao={validacao} como="div">
              <input
                type="date"
                value={segmento.data_fim ?? ""}
                placeholder="data do cálculo"
                onChange={(e) => atualizar(i, "data_fim", e.target.value || null)}
              />
            </Campo>
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
