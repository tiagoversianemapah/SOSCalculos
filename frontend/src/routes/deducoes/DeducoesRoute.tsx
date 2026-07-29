// Passo "Deduções" (paridade SOSCálculos) — só existe quando
// `Processo.configura_deducoes` é true (ver especificacao-tecnica-motor-
// -calculo-judicial.md seção 4/11). Cada linha tem valor e data
// próprios, e pode ter Correção Monetária/Juros Moratórios próprios
// (mesmo mecanismo default/sem/personalizado do passo 2/3) — o valor
// corrigido é subtraído do total geral, não do saldo de uma parcela
// específica.
import { Fragment, useEffect, useRef, useState } from "react";
import { CorrecaoSegmentoEditor } from "../../components/forms/CorrecaoSegmentoEditor";
import { JurosSegmentoEditor } from "../../components/forms/JurosSegmentoEditor";
import { api, mensagemDeErro } from "../../lib/api";
import { rotularCorrecaoDefault, rotularJurosDefault } from "../../lib/rotulos";
import type { Deducao, Processo, TipoAtualizacaoDeducao, TipoDeducao, TipoVencimento } from "../../lib/types";
import { TIPOS_ATUALIZACAO_DEDUCAO, TIPOS_DEDUCAO } from "../../lib/types";
import { useWizard } from "../../store/wizardStore";

type OpcaoDefault = "default" | "sem" | "personalizado";

function opcaoCorrecao(d: Deducao): OpcaoDefault {
  if (d.usa_correcao_default) return "default";
  return d.correcao_segmentos_override.length > 0 ? "personalizado" : "sem";
}

function opcaoJuros(d: Deducao): OpcaoDefault {
  if (d.usa_juros_default) return "default";
  return d.juros_segmentos_override.length > 0 ? "personalizado" : "sem";
}

function rascunhoVazio(): Omit<Deducao, "id" | "correcao_segmentos_override" | "juros_segmentos_override"> {
  return {
    tipo: "pagamento",
    historico: "",
    data_inicial: "",
    valor: "",
    atualizacao_tipo: "data_inicial",
    data_atualizacao: null,
    usa_correcao_default: true,
    usa_juros_default: true,
  };
}

export function DeducoesRoute() {
  const { processoId, irParaPasso } = useWizard();
  const [processo, setProcesso] = useState<Processo | null>(null);
  const [itens, setItens] = useState<Deducao[]>([]);
  const itensRef = useRef<Deducao[]>([]);
  itensRef.current = itens;
  const [rascunho, setRascunho] = useState(rascunhoVazio());
  const [erro, setErro] = useState<string | null>(null);
  const [expandido, setExpandido] = useState<string | null>(null);

  const recarregar = () => {
    if (!processoId) return;
    api.deducoes.listar(processoId).then(setItens);
  };

  useEffect(() => {
    if (!processoId) return;
    api.processos.obter(processoId).then(setProcesso);
    recarregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processoId]);

  if (!processoId || !processo) return <p>Carregando…</p>;

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

  const salvar = async (id: string, patch: Partial<Deducao>) => {
    setErro(null);
    const atual = itensRef.current.find((it) => it.id === id);
    if (!atual) return;
    const atualizado = { ...atual, ...patch };
    itensRef.current = itensRef.current.map((it) => (it.id === id ? atualizado : it));
    setItens(itensRef.current);
    try {
      await api.deducoes.atualizar(id, atualizado);
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const trocarOpcaoCorrecao = (d: Deducao, opcao: OpcaoDefault) => {
    if (opcao === "default") return salvar(d.id, { usa_correcao_default: true, correcao_segmentos_override: [] });
    if (opcao === "sem") return salvar(d.id, { usa_correcao_default: false, correcao_segmentos_override: [] });
    setExpandido(d.id);
    if (d.correcao_segmentos_override.length === 0) {
      salvar(d.id, {
        usa_correcao_default: false,
        correcao_segmentos_override: [
          {
            ordem: 1,
            indice: "ipca",
            data_inicio: d.data_inicial,
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

  const trocarOpcaoJuros = (d: Deducao, opcao: OpcaoDefault) => {
    if (opcao === "default") return salvar(d.id, { usa_juros_default: true, juros_segmentos_override: [] });
    if (opcao === "sem") return salvar(d.id, { usa_juros_default: false, juros_segmentos_override: [] });
    setExpandido(d.id);
    if (d.juros_segmentos_override.length === 0) {
      salvar(d.id, {
        usa_juros_default: false,
        juros_segmentos_override: [
          {
            ordem: 1,
            tipo_taxa: "percentual_fixo_mensal",
            taxa_valor: "0.01",
            data_inicio: d.data_inicial,
            data_fim: null,
            fonte_criterio: "",
            vencimento_tipo: "do_vencimento",
          },
        ],
      });
    }
  };

  const adicionar = async () => {
    setErro(null);
    const faltando: string[] = [];
    if (!rascunho.data_inicial) faltando.push("Data Inicial");
    if (!rascunho.valor) faltando.push("Valor");
    if (faltando.length > 0) {
      setErro(`Preencha antes de adicionar a linha: ${faltando.join(", ")}.`);
      return;
    }
    try {
      await api.deducoes.criar(processoId, rascunho);
      setRascunho(rascunhoVazio());
      recarregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const remover = async (id: string) => {
    await api.deducoes.remover(id);
    recarregar();
  };

  return (
    <div className="rota-deducoes">
      <h2>Liquidação de Sentença — Cálculo Judicial (Deduções)</h2>
      <p className="texto-auxiliar">
        Informe as deduções para a liquidação de sentença — cada uma pode ter correção monetária e
        juros próprios; o valor corrigido é subtraído do total geral.
      </p>
      {erro && <p className="erro">{erro}</p>}

      <div className="tabela-scroll">
        <table className="tabela-creditos">
          <thead>
            <tr>
              <th>Nº</th>
              <th>Tipo</th>
              <th>Data Inicial *</th>
              <th>Histórico</th>
              <th>Valor *</th>
              <th>Atualização</th>
              <th>Data Atualização</th>
              <th>Correção Monetária</th>
              <th>Juros Moratórios</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {itens.map((d, i) => {
              const precisaDataAtualizacao = d.atualizacao_tipo === "outra_data" || d.atualizacao_tipo === "data_levantamento";
              return (
                <Fragment key={d.id}>
                  <tr>
                    <td>{i + 1}</td>
                    <td>
                      <select value={d.tipo} onChange={(e) => salvar(d.id, { tipo: e.target.value as TipoDeducao })}>
                        {TIPOS_DEDUCAO.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="date"
                        value={d.data_inicial}
                        onChange={(e) => salvar(d.id, { data_inicial: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        defaultValue={d.historico ?? ""}
                        onBlur={(e) => salvar(d.id, { historico: e.target.value })}
                      />
                    </td>
                    <td>
                      <input placeholder="0,00" defaultValue={d.valor} onBlur={(e) => salvar(d.id, { valor: e.target.value })} />
                    </td>
                    <td>
                      <select
                        value={d.atualizacao_tipo}
                        onChange={(e) => salvar(d.id, { atualizacao_tipo: e.target.value as TipoAtualizacaoDeducao })}
                      >
                        {TIPOS_ATUALIZACAO_DEDUCAO.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="date"
                        disabled={!precisaDataAtualizacao}
                        value={d.data_atualizacao ?? ""}
                        onChange={(e) => salvar(d.id, { data_atualizacao: e.target.value || null })}
                      />
                    </td>
                    <td>
                      <select value={opcaoCorrecao(d)} onChange={(e) => trocarOpcaoCorrecao(d, e.target.value as OpcaoDefault)}>
                        <option value="default">{rotuloCorrecao}</option>
                        <option value="sem">Sem Correção Monetária</option>
                        <option value="personalizado">Personalizado…</option>
                      </select>
                    </td>
                    <td>
                      <select value={opcaoJuros(d)} onChange={(e) => trocarOpcaoJuros(d, e.target.value as OpcaoDefault)}>
                        <option value="default">{rotuloJuros}</option>
                        <option value="sem">Sem Juros</option>
                        <option value="personalizado">Personalizado…</option>
                      </select>
                    </td>
                    <td>
                      <button type="button" onClick={() => setExpandido(expandido === d.id ? null : d.id)}>
                        {expandido === d.id ? "fechar" : "editar"}
                      </button>
                      <button type="button" onClick={() => remover(d.id)}>
                        remover
                      </button>
                    </td>
                  </tr>
                  {expandido === d.id && (
                    <tr>
                      <td colSpan={10}>
                        <div className="parcela-detalhe">
                          {opcaoCorrecao(d) === "personalizado" && (
                            <CorrecaoSegmentoEditor
                              segmentos={d.correcao_segmentos_override}
                              onChange={(segmentos) => salvar(d.id, { correcao_segmentos_override: segmentos })}
                              datasAncora={datasAncora}
                            />
                          )}
                          {opcaoJuros(d) === "personalizado" && (
                            <JurosSegmentoEditor
                              segmentos={d.juros_segmentos_override}
                              onChange={(segmentos) => salvar(d.id, { juros_segmentos_override: segmentos })}
                              datasAncora={datasAncora}
                            />
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            <tr>
              <td>{itens.length + 1}</td>
              <td>
                <select value={rascunho.tipo} onChange={(e) => setRascunho({ ...rascunho, tipo: e.target.value as TipoDeducao })}>
                  {TIPOS_DEDUCAO.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <input type="date" value={rascunho.data_inicial} onChange={(e) => setRascunho({ ...rascunho, data_inicial: e.target.value })} />
              </td>
              <td>
                <input value={rascunho.historico ?? ""} onChange={(e) => setRascunho({ ...rascunho, historico: e.target.value })} />
              </td>
              <td>
                <input placeholder="0,00" value={rascunho.valor} onChange={(e) => setRascunho({ ...rascunho, valor: e.target.value })} />
              </td>
              <td colSpan={4} />
              <td>
                <button type="button" onClick={adicionar}>
                  + adicionar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="acoes-rodape">
        <button type="button" onClick={() => irParaPasso(3)}>
          ← voltar
        </button>
        <button type="button" className="primario" onClick={() => irParaPasso(5)}>
          Continuar →
        </button>
      </div>
    </div>
  );
}
