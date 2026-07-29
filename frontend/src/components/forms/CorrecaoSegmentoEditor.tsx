// Editor de lista ordenada de segmentos de correção monetária —
// reutilizado no passo 1 (default do processo) e no passo 2 (override
// da parcela), seção 6.2. Os campos "Vencimento da C.M.", "Deflação" e
// "Compor com Selic" replicam a linha de configuração do SOSCálculos
// (paridade, seção 0/2) — ver CorrecaoSegmentoEditor no
// especificacao-tecnica-motor-calculo-judicial.md.
import { Icone } from "../ui/Icone";
import type { CorrecaoSegmento, Indice, TipoVencimento } from "../../lib/types";
import { INDICES, TIPOS_VENCIMENTO } from "../../lib/types";
import { Campo, VALIDACAO_INERTE, obrigatorio, type RegraCampo, type Validacao } from "../../lib/validacao";

interface Props {
  segmentos: CorrecaoSegmento[];
  onChange: (segmentos: CorrecaoSegmento[]) => void;
  // Datas-âncora do processo (data_citacao, data_sentenca, etc.) — usadas
  // só pra pré-preencher data_inicio quando o usuário troca "Vencimento
  // da C.M."; se a âncora escolhida não tiver data preenchida ainda, o
  // campo de data fica em branco pro usuário digitar.
  datasAncora?: Partial<Record<TipoVencimento, string | null | undefined>>;
  // Validação por campo (ver lib/validacao.tsx). `prefixo` isola os nomes
  // quando há vários editores na mesma tela (um por parcela, por exemplo).
  validacao?: Validacao;
  prefixo?: string;
}

/** Regras dos campos deste editor — fica aqui junto do JSX para os dois
 * não saírem de sincronia. `revelar` abre a seção que contém o editor
 * quando ele está recolhido (linha "editar" da planilha). */
export function regrasCorrecao(
  prefixo: string,
  segmentos: CorrecaoSegmento[],
  revelar?: () => void
): RegraCampo[] {
  const regras: RegraCampo[] = [];
  segmentos.forEach((segmento, i) => {
    regras.push(obrigatorio(`${prefixo}${i}.data_inicio`, segmento.data_inicio, "A data inicial", revelar));
    // Campo condicional: só existe na tela quando o índice é "tribunal".
    if (segmento.indice === "tribunal") {
      regras.push(
        obrigatorio(`${prefixo}${i}.tribunal_codigo`, segmento.tribunal_codigo, "O código do tribunal", revelar)
      );
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

function novoSegmento(ordem: number): CorrecaoSegmento {
  return {
    ordem,
    indice: "ipca",
    data_inicio: "",
    data_fim: null,
    fonte_criterio: "",
    vencimento_tipo: "do_vencimento",
    permite_deflacao: true,
    compor_com_selic: false,
  };
}

export function CorrecaoSegmentoEditor({
  segmentos,
  onChange,
  datasAncora,
  validacao = VALIDACAO_INERTE,
  prefixo = "correcao.",
}: Props) {
  const atualizar = (indice: number, campo: keyof CorrecaoSegmento, valor: unknown) => {
    const copia = segmentos.map((s, i) => (i === indice ? { ...s, [campo]: valor } : s));
    onChange(copia);
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
      <h4>Correção monetária</h4>
      {segmentos.length === 0 && <p className="texto-auxiliar">Nenhum segmento — sem correção.</p>}
      {segmentos.map((segmento, i) => (
        <div className="segmento-bloco" key={i}>
          <div className="segmento-linha">
            <select
              value={segmento.indice}
              onChange={(e) => atualizar(i, "indice", e.target.value as Indice)}
            >
              {INDICES.map((opcao) => (
                <option key={opcao.value} value={opcao.value}>
                  {opcao.label}
                </option>
              ))}
            </select>
            {segmento.indice === "tribunal" && (
              <Campo nome={`${prefixo}${i}.tribunal_codigo`} validacao={validacao} como="div">
                <input
                  placeholder="código do tribunal (ex.: TJGO)"
                  value={segmento.tribunal_codigo ?? ""}
                  onChange={(e) => atualizar(i, "tribunal_codigo", e.target.value)}
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
              placeholder="fonte do critério (ex.: sentença, fls. 312)"
              value={segmento.fonte_criterio ?? ""}
              onChange={(e) => atualizar(i, "fonte_criterio", e.target.value)}
            />
            <button
              type="button"
              className="icone-so"
              onClick={() => remover(i)}
              aria-label="Remover segmento"
              title="Remover segmento"
            >
              <Icone nome="lixeira" tamanho={14} />
            </button>
          </div>
          <div className="segmento-linha segmento-linha-config">
            <label>
              Vencimento da C.M.
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
            <label>
              Deflação (índices negativos)
              <select
                value={segmento.permite_deflacao ? "com" : "sem"}
                onChange={(e) => atualizar(i, "permite_deflacao", e.target.value === "com")}
              >
                <option value="com">Com deflação</option>
                <option value="sem">Sem deflação</option>
              </select>
            </label>
            <label>
              Compor com Selic
              <select
                value={segmento.compor_com_selic ? "sim" : "nao"}
                onChange={(e) => atualizar(i, "compor_com_selic", e.target.value === "sim")}
              >
                <option value="nao">Não</option>
                <option value="sim">Sim</option>
              </select>
            </label>
          </div>
        </div>
      ))}
      <button type="button" className="adicionar" onClick={adicionar}>
        <Icone nome="mais" tamanho={14} />
        adicionar tabela de correção
      </button>
    </div>
  );
}
