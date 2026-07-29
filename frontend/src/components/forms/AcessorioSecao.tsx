// Seção genérica do passo 3 (Honorários de Sucumbência, Outros
// Honorários Execução, Multas, Custas Processuais — paridade
// SOSCálculos). Cada linha escolhe um "Tipo" que decide a base de
// cálculo: percentual sobre a condenação, percentual sobre o valor da
// causa, ou um valor monetário fixo com correção/juros próprios (mesmo
// mecanismo "default do processo / sem / personalizado" do passo 2).
import { useEffect, useRef, useState } from "react";
import { api, mensagemDeErro } from "../../lib/api";
import { rotularCorrecaoDefault, rotularJurosDefault } from "../../lib/rotulos";
import type { Acessorio, BaseCalculoAcessorio, Processo, TipoAcessorio, TipoVencimento } from "../../lib/types";
import { CorrecaoSegmentoEditor } from "./CorrecaoSegmentoEditor";
import { JurosSegmentoEditor } from "./JurosSegmentoEditor";

export type Subtipo = "condenacao" | "causa" | "valor_monetario" | "diaria_data_final";

const ROTULO_SUBTIPO: Record<Subtipo, string> = {
  condenacao: "Sobre o Valor da Condenação",
  causa: "Sobre o Valor da Causa",
  valor_monetario: "Valor Monetário",
  diaria_data_final: "Diária (Data final)",
};

const BASE_DO_SUBTIPO: Record<Subtipo, BaseCalculoAcessorio> = {
  condenacao: "total_liquido_parcelas",
  causa: "valor_da_causa",
  valor_monetario: "valor_fixo_absoluto",
  diaria_data_final: "valor_fixo_absoluto",
};

function subtipoDoAcessorio(a: Acessorio): Subtipo {
  if (a.valor_diario != null) return "diaria_data_final";
  if (a.base_calculo === "valor_fixo_absoluto") return "valor_monetario";
  if (a.base_calculo === "valor_da_causa") return "causa";
  return "condenacao";
}

type OpcaoDefault = "default" | "sem" | "personalizado";

function opcaoCorrecao(a: Acessorio): OpcaoDefault {
  if (a.usa_correcao_default) return "default";
  return a.correcao_segmentos_override.length > 0 ? "personalizado" : "sem";
}

function opcaoJuros(a: Acessorio): OpcaoDefault {
  if (a.usa_juros_default) return "default";
  return a.juros_segmentos_override.length > 0 ? "personalizado" : "sem";
}

interface Props {
  titulo: string;
  processoId: string;
  processo: Processo;
  tipoAcessorio: TipoAcessorio;
  acessorios: Acessorio[];
  subtiposPermitidos: Subtipo[];
  subtiposDesabilitados?: { subtipo: string; rotulo: string }[];
  onMudou: () => void;
}

export function AcessorioSecao({
  titulo,
  processoId,
  processo,
  tipoAcessorio,
  acessorios,
  subtiposPermitidos,
  subtiposDesabilitados = [],
  onMudou,
}: Props) {
  const [erro, setErro] = useState<string | null>(null);
  const [expandido, setExpandido] = useState<string | null>(null);
  // Estado local otimista — evita que dois campos editados em sequência
  // rápida (ex.: Início e Fim da multa diária) percam um ao outro: cada
  // salvar() atualiza esta lista ANTES do round-trip da rede, então o
  // segundo PUT já parte da versão mais recente, não da prop desatualizada.
  const [itens, setItens] = useState<Acessorio[]>(acessorios);
  useEffect(() => setItens(acessorios), [acessorios]);
  // Ref sempre sincronizada com `itens` — usada por salvar() pra nunca
  // basear um patch num `a` capturado num closure de render antigo
  // (mesma classe de bug já corrigida em wizardStore.tsx).
  const itensRef = useRef(itens);
  itensRef.current = itens;

  const datasAncora: Partial<Record<TipoVencimento, string | null | undefined>> = {
    da_citacao: processo.data_citacao,
    da_distribuicao: processo.data_distribuicao,
    da_sentenca: processo.data_sentenca,
    do_evento: processo.data_evento_padrao,
    do_transito_julgado: processo.data_transito_julgado,
    da_publicacao: processo.data_publicacao,
    da_data_fixa: processo.data_fixa,
    da_homologacao: processo.data_homologacao,
    da_aposentadoria: processo.data_aposentadoria,
  };
  const rotuloCorrecao = rotularCorrecaoDefault(processo.correcao_segmentos_default);
  const rotuloJuros = rotularJurosDefault(processo.juros_segmentos_default);

  const hoje = new Date().toISOString().slice(0, 10);

  const adicionar = async () => {
    setErro(null);
    try {
      const subtipo = subtiposPermitidos[0];
      const monetario = subtipo === "valor_monetario";
      const diaria = subtipo === "diaria_data_final";
      await api.acessorios.criar(processoId, {
        tipo: tipoAcessorio,
        historico: "",
        base_calculo: BASE_DO_SUBTIPO[subtipo],
        percentual: monetario || diaria ? null : "0",
        valor_fixo: monetario ? "0" : null,
        data_evento: monetario || diaria ? hoje : null,
        valor_diario: diaria ? "0" : null,
        data_inicio_acumulo: diaria ? hoje : null,
        usa_correcao_default: true,
        usa_juros_default: true,
      });
      onMudou();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const salvar = async (id: string, patch: Partial<Acessorio>) => {
    setErro(null);
    const atual = itensRef.current.find((it) => it.id === id);
    if (!atual) return;
    const atualizado = { ...atual, ...patch };
    itensRef.current = itensRef.current.map((it) => (it.id === id ? atualizado : it));
    setItens(itensRef.current);
    try {
      await api.acessorios.atualizar(id, atualizado);
      onMudou();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const trocarSubtipo = (a: Acessorio, subtipo: Subtipo) => {
    if (subtipo === "valor_monetario") {
      salvar(a.id, {
        base_calculo: "valor_fixo_absoluto",
        percentual: null,
        valor_fixo: a.valor_fixo ?? "0",
        data_evento: a.data_evento ?? hoje,
        valor_diario: null,
        data_inicio_acumulo: null,
      });
    } else if (subtipo === "diaria_data_final") {
      salvar(a.id, {
        base_calculo: "valor_fixo_absoluto",
        percentual: null,
        valor_fixo: null,
        valor_diario: a.valor_diario ?? "0",
        data_inicio_acumulo: a.data_inicio_acumulo ?? hoje,
        data_evento: a.data_evento ?? hoje,
      });
    } else {
      salvar(a.id, {
        base_calculo: BASE_DO_SUBTIPO[subtipo],
        percentual: a.percentual ?? "0",
        valor_fixo: null,
        valor_diario: null,
        data_inicio_acumulo: null,
      });
    }
  };

  const trocarOpcaoCorrecao = (a: Acessorio, opcao: OpcaoDefault) => {
    if (opcao === "default") return salvar(a.id, { usa_correcao_default: true, correcao_segmentos_override: [] });
    if (opcao === "sem") return salvar(a.id, { usa_correcao_default: false, correcao_segmentos_override: [] });
    setExpandido(a.id);
    if (a.correcao_segmentos_override.length === 0) {
      salvar(a.id, {
        usa_correcao_default: false,
        correcao_segmentos_override: [
          {
            ordem: 1,
            indice: "ipca",
            data_inicio: a.data_evento ?? "",
            data_fim: null,
            fonte_criterio: "",
            vencimento_tipo: "do_vencimento",
            permite_deflacao: true,
            compor_com_selic: false,
          },
        ],
      });
    }
  };

  const trocarOpcaoJuros = (a: Acessorio, opcao: OpcaoDefault) => {
    if (opcao === "default") return salvar(a.id, { usa_juros_default: true, juros_segmentos_override: [] });
    if (opcao === "sem") return salvar(a.id, { usa_juros_default: false, juros_segmentos_override: [] });
    setExpandido(a.id);
    if (a.juros_segmentos_override.length === 0) {
      salvar(a.id, {
        usa_juros_default: false,
        juros_segmentos_override: [
          {
            ordem: 1,
            tipo_taxa: "percentual_fixo_mensal",
            taxa_valor: "0.01",
            data_inicio: a.data_evento ?? "",
            data_fim: null,
            fonte_criterio: "",
            vencimento_tipo: "do_vencimento",
          },
        ],
      });
    }
  };

  const remover = async (id: string) => {
    await api.acessorios.remover(id);
    onMudou();
  };

  return (
    <section className="secao-formulario secao-acessorio">
      <h3>{titulo}</h3>
      {erro && <p className="erro">{erro}</p>}
      {itens.map((a) => {
        const subtipo = subtipoDoAcessorio(a);
        const monetario = subtipo === "valor_monetario";
        const diaria = subtipo === "diaria_data_final";
        const temCorrecaoPropria = monetario || diaria;
        return (
          <div className="segmento-bloco" key={a.id}>
            <div className="segmento-linha">
              <select value={subtipo} onChange={(e) => trocarSubtipo(a, e.target.value as Subtipo)}>
                {subtiposPermitidos.map((s) => (
                  <option key={s} value={s}>
                    {ROTULO_SUBTIPO[s]}
                  </option>
                ))}
                {subtiposDesabilitados.map((s) => (
                  <option key={s.subtipo} value={s.subtipo} disabled>
                    {s.rotulo} (em breve)
                  </option>
                ))}
              </select>
              <input
                placeholder="Histórico"
                defaultValue={a.historico ?? ""}
                onBlur={(e) => salvar(a.id, { historico: e.target.value })}
              />
              {!monetario && !diaria && (
                <input
                  placeholder="% (ex.: 0.10 = 10%)"
                  defaultValue={a.percentual ?? ""}
                  onBlur={(e) => salvar(a.id, { percentual: e.target.value })}
                />
              )}
              {monetario && (
                <>
                  <input
                    placeholder="Valor"
                    defaultValue={a.valor_fixo ?? ""}
                    onBlur={(e) => salvar(a.id, { valor_fixo: e.target.value })}
                  />
                  <input
                    type="date"
                    value={a.data_evento ?? ""}
                    onChange={(e) => salvar(a.id, { data_evento: e.target.value || null })}
                  />
                </>
              )}
              {diaria && (
                <>
                  <input
                    placeholder="Valor diário"
                    defaultValue={a.valor_diario ?? ""}
                    onBlur={(e) => salvar(a.id, { valor_diario: e.target.value })}
                  />
                  <label className="campo-inline">
                    Início
                    <input
                      type="date"
                      value={a.data_inicio_acumulo ?? ""}
                      onChange={(e) => salvar(a.id, { data_inicio_acumulo: e.target.value || null })}
                    />
                  </label>
                  <label className="campo-inline">
                    Fim
                    <input
                      type="date"
                      value={a.data_evento ?? ""}
                      onChange={(e) => salvar(a.id, { data_evento: e.target.value || null })}
                    />
                  </label>
                </>
              )}
              <button type="button" onClick={() => setExpandido(expandido === a.id ? null : a.id)}>
                {expandido === a.id ? "fechar" : "editar"}
              </button>
              <button type="button" onClick={() => remover(a.id)} aria-label="Remover">
                ✕
              </button>
            </div>
            {temCorrecaoPropria && (
              <div className="segmento-linha segmento-linha-config">
                <label>
                  Tabela de C.M.
                  <select value={opcaoCorrecao(a)} onChange={(e) => trocarOpcaoCorrecao(a, e.target.value as OpcaoDefault)}>
                    <option value="default">{rotuloCorrecao}</option>
                    <option value="sem">Sem Correção Monetária</option>
                    <option value="personalizado">Personalizado…</option>
                  </select>
                </label>
                <label>
                  Juros de Mora
                  <select value={opcaoJuros(a)} onChange={(e) => trocarOpcaoJuros(a, e.target.value as OpcaoDefault)}>
                    <option value="default">{rotuloJuros}</option>
                    <option value="sem">Sem Juros</option>
                    <option value="personalizado">Personalizado…</option>
                  </select>
                </label>
              </div>
            )}
            {expandido === a.id && (
              <div className="parcela-detalhe">
                {temCorrecaoPropria && opcaoCorrecao(a) === "personalizado" && (
                  <CorrecaoSegmentoEditor
                    segmentos={a.correcao_segmentos_override}
                    onChange={(segmentos) => salvar(a.id, { correcao_segmentos_override: segmentos })}
                    datasAncora={datasAncora}
                  />
                )}
                {temCorrecaoPropria && opcaoJuros(a) === "personalizado" && (
                  <JurosSegmentoEditor
                    segmentos={a.juros_segmentos_override}
                    onChange={(segmentos) => salvar(a.id, { juros_segmentos_override: segmentos })}
                    datasAncora={datasAncora}
                  />
                )}
                <label>
                  Fonte do critério <span className="campo-opcional">(opcional)</span>
                  <input
                    defaultValue={a.fonte_criterio ?? ""}
                    onBlur={(e) => salvar(a.id, { fonte_criterio: e.target.value })}
                  />
                </label>
              </div>
            )}
          </div>
        );
      })}
      <button type="button" onClick={adicionar}>
        + Add {titulo}
      </button>
    </section>
  );
}
