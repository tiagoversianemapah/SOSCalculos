// Passo 2 — Créditos (parcelas), planilha única (paridade SOSCálculos,
// ver especificacao-tecnica-motor-calculo-judicial.md seção 0/4). Cada
// linha é uma parcela; os dropdowns de Correção/Juros escolhem entre a
// configuração padrão do processo (passo 1) ou "sem correção"/"sem
// juros" — configuração avançada (segmentos próprios da parcela) fica
// atrás do botão "editar", que também dá acesso às deduções datadas
// (pagamento_parcial). "Importar" (PDF) fica de fora por enquanto —
// sem exemplo real do que o SOSCálculos extrai (ver especificação, seção 11).
import { Fragment, useEffect, useState } from "react";
import { CorrecaoSegmentoEditor, regrasCorrecao } from "../../components/forms/CorrecaoSegmentoEditor";
import { JurosSegmentoEditor, regrasJuros } from "../../components/forms/JurosSegmentoEditor";
import { PreenchimentoSerieModal } from "../../components/forms/PreenchimentoSerieModal";
import { SalarioMinimoModal } from "../../components/forms/SalarioMinimoModal";
import { PagamentoTable } from "../../components/tables/PagamentoTable";
import { api, mensagemDeErro } from "../../lib/api";
import { formatarMoeda } from "../../lib/format";
import { rotularCorrecaoDefault, rotularJurosDefault } from "../../lib/rotulos";
import type { Parcela, Processo } from "../../lib/types";
import { Campo, obrigatorio, useValidacao, type RegraCampo, type Validacao } from "../../lib/validacao";
import { useWizard } from "../../store/wizardStore";

type OpcaoDefault = "default" | "sem" | "personalizado";

function rascunhoVazio(): Omit<Parcela, "id" | "processo_id" | "valor_apurado" | "pagamentos"> {
  return {
    vencimento: "",
    historico: "",
    valor_bruto: "",
    usa_correcao_default: true,
    usa_juros_default: true,
    multa_percentual: null,
    correcao_segmentos_override: [],
    juros_segmentos_override: [],
  };
}

function opcaoCorrecao(p: { usa_correcao_default: boolean; correcao_segmentos_override: unknown[] }): OpcaoDefault {
  if (p.usa_correcao_default) return "default";
  return p.correcao_segmentos_override.length > 0 ? "personalizado" : "sem";
}

function opcaoJuros(p: { usa_juros_default: boolean; juros_segmentos_override: unknown[] }): OpcaoDefault {
  if (p.usa_juros_default) return "default";
  return p.juros_segmentos_override.length > 0 ? "personalizado" : "sem";
}

function percentualParaExibicao(fracao: string | null | undefined): string {
  if (!fracao) return "";
  return (Number(fracao) * 100).toString();
}

function regraValorMonetario(nome: string, valor: string, rotulo: string): RegraCampo {
  if (!valor || !valor.trim()) {
    return { nome, valido: false, mensagem: `${rotulo} é obrigatório.` };
  }
  return {
    nome,
    valido: !Number.isNaN(Number(valor)) && Number(valor) > 0,
    mensagem: "Informe um valor numérico maior que zero (ex.: 1500.00).",
  };
}

export function CreditosRoute() {
  const { processoId, irParaPasso } = useWizard();
  const [processo, setProcesso] = useState<Processo | null>(null);
  const [parcelas, setParcelas] = useState<Parcela[]>([]);
  const [expandida, setExpandida] = useState<string | null>(null);
  const [rascunho, setRascunho] = useState(rascunhoVazio());
  // Só falha de servidor — campo faltando aparece no próprio campo.
  const [erro, setErro] = useState<string | null>(null);
  const [modalSerie, setModalSerie] = useState(false);
  const [modalSalarioMinimo, setModalSalarioMinimo] = useState(false);
  const validacao = useValidacao();

  const recarregar = () => {
    if (!processoId) return;
    api.parcelas.listar(processoId).then(setParcelas);
  };

  useEffect(() => {
    if (!processoId) return;
    api.processos.obter(processoId).then(setProcesso);
    recarregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processoId]);

  const rotuloCorrecao = processo ? rotularCorrecaoDefault(processo.correcao_segmentos_default) : "Correção do processo";
  const rotuloJuros = processo ? rotularJurosDefault(processo.juros_segmentos_default) : "Juros do processo";

  const salvarParcela = async (id: string, patch: Partial<Parcela>) => {
    const atual = parcelas.find((p) => p.id === id);
    if (!atual) return;
    setErro(null);
    try {
      const salvo = await api.parcelas.atualizar(id, { ...atual, ...patch });
      setParcelas((atuais) => atuais.map((p) => (p.id === id ? salvo : p)));
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const trocarOpcaoCorrecao = (id: string, opcao: OpcaoDefault) => {
    if (opcao === "default") return salvarParcela(id, { usa_correcao_default: true, correcao_segmentos_override: [] });
    if (opcao === "sem") return salvarParcela(id, { usa_correcao_default: false, correcao_segmentos_override: [] });
    setExpandida(id);
    const atual = parcelas.find((p) => p.id === id);
    if (atual && atual.correcao_segmentos_override.length === 0) {
      salvarParcela(id, {
        usa_correcao_default: false,
        correcao_segmentos_override: [
          {
            ordem: 1,
            indice: "ipca",
            data_inicio: atual.vencimento,
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

  const trocarOpcaoJuros = (id: string, opcao: OpcaoDefault) => {
    if (opcao === "default") return salvarParcela(id, { usa_juros_default: true, juros_segmentos_override: [] });
    if (opcao === "sem") return salvarParcela(id, { usa_juros_default: false, juros_segmentos_override: [] });
    setExpandida(id);
    const atual = parcelas.find((p) => p.id === id);
    if (atual && atual.juros_segmentos_override.length === 0) {
      salvarParcela(id, {
        usa_juros_default: false,
        juros_segmentos_override: [
          {
            ordem: 1,
            tipo_taxa: "percentual_fixo_mensal",
            taxa_valor: "0.01",
            data_inicio: atual.vencimento,
            data_fim: null,
            fonte_criterio: "",
            vencimento_tipo: "do_vencimento",
          },
        ],
      });
    }
  };

  const adicionar = async () => {
    if (!processoId) return;
    setErro(null);
    const regras: RegraCampo[] = [
      obrigatorio("rascunho.vencimento", rascunho.vencimento, "O vencimento"),
      obrigatorio("rascunho.historico", rascunho.historico, "O histórico"),
      regraValorMonetario("rascunho.valor_bruto", rascunho.valor_bruto, "O valor bruto"),
    ];
    if (!validacao.validar(regras)) return;
    try {
      await api.parcelas.criar(processoId, rascunho);
      setRascunho(rascunhoVazio());
      recarregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const continuar = () => {
    setErro(null);
    if (parcelas.length === 0) {
      // Sem nenhuma parcela ainda: leva o usuário pra linha em branco no
      // fim da planilha, que é onde ele precisa digitar.
      validacao.validar([
        {
          nome: "rascunho.vencimento",
          valido: false,
          mensagem: "Adicione pelo menos uma parcela antes de continuar.",
        },
      ]);
      return;
    }
    // Linhas já criadas podem ter sido esvaziadas na edição inline, e os
    // segmentos "Personalizado…" ficam escondidos atrás do botão "editar"
    // — por isso cada regra desses leva um `revelar` que abre a linha.
    const regras: RegraCampo[] = [];
    for (const parcela of parcelas) {
      const abrirLinha = () => setExpandida(parcela.id);
      regras.push(obrigatorio(`parcela.${parcela.id}.vencimento`, parcela.vencimento, "O vencimento"));
      regras.push(obrigatorio(`parcela.${parcela.id}.historico`, parcela.historico, "O histórico"));
      regras.push(regraValorMonetario(`parcela.${parcela.id}.valor_bruto`, parcela.valor_bruto, "O valor bruto"));
      if (!parcela.usa_correcao_default && parcela.correcao_segmentos_override.length > 0) {
        regras.push(
          ...regrasCorrecao(`parcela.${parcela.id}.correcao.`, parcela.correcao_segmentos_override, abrirLinha)
        );
      }
      if (!parcela.usa_juros_default && parcela.juros_segmentos_override.length > 0) {
        regras.push(...regrasJuros(`parcela.${parcela.id}.juros.`, parcela.juros_segmentos_override, abrirLinha));
      }
    }
    if (!validacao.validar(regras)) return;
    irParaPasso(3);
  };

  const remover = async (id: string) => {
    await api.parcelas.remover(id);
    recarregar();
  };

  const totalPago = (p: Parcela) => p.pagamentos.reduce((soma, pg) => soma + Number(pg.valor), 0).toFixed(2);

  return (
    <div className="rota-creditos">
      <h2>Liquidação de Sentença — Cálculo Judicial (Passo 2)</h2>
      <p className="texto-auxiliar">Neste passo, informe todos os "créditos" para a liquidação de sentença.</p>
      {erro && <p className="erro">{erro}</p>}

      <div className="barra-acoes-creditos">
        <button type="button" disabled={!processoId} onClick={() => setModalSerie(true)}>
          Preenchimento Em Série
        </button>
        <button type="button" disabled={!processoId} onClick={() => setModalSalarioMinimo(true)}>
          Salário Mínimo
        </button>
        <button type="button" disabled title="Ainda não disponível — importação a partir de PDF">
          Importar
        </button>
      </div>

      <div className="tabela-scroll">
        <table className="tabela-creditos">
          <thead>
            <tr>
              <th>Nº</th>
              <th>Vencimento/Exigibilidade *</th>
              <th>Histórico *</th>
              <th>Vlr Bruto *</th>
              <th>Valor Pago</th>
              <th>Vlr Apurado</th>
              <th>Correção Monetária</th>
              <th>Juros Moratórios</th>
              <th>Multa %</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {parcelas.map((parcela, i) => (
              <Fragment key={parcela.id}>
                <tr>
                  <td>{i + 1}</td>
                  <td>
                    <Campo nome={`parcela.${parcela.id}.vencimento`} validacao={validacao} como="div">
                      <input
                        type="date"
                        value={parcela.vencimento}
                        onChange={(e) => setParcelas((ps) => ps.map((p) => (p.id === parcela.id ? { ...p, vencimento: e.target.value } : p)))}
                        onBlur={(e) => salvarParcela(parcela.id, { vencimento: e.target.value })}
                      />
                    </Campo>
                  </td>
                  <td>
                    <Campo nome={`parcela.${parcela.id}.historico`} validacao={validacao} como="div">
                      <input
                        value={parcela.historico}
                        onChange={(e) => setParcelas((ps) => ps.map((p) => (p.id === parcela.id ? { ...p, historico: e.target.value } : p)))}
                        onBlur={(e) => salvarParcela(parcela.id, { historico: e.target.value })}
                      />
                    </Campo>
                  </td>
                  <td>
                    <Campo nome={`parcela.${parcela.id}.valor_bruto`} validacao={validacao} como="div">
                      <input
                        placeholder="0,00"
                        value={parcela.valor_bruto}
                        onChange={(e) => setParcelas((ps) => ps.map((p) => (p.id === parcela.id ? { ...p, valor_bruto: e.target.value } : p)))}
                        onBlur={(e) => salvarParcela(parcela.id, { valor_bruto: e.target.value })}
                      />
                    </Campo>
                  </td>
                  <td className="celula-somente-leitura">{formatarMoeda(totalPago(parcela))}</td>
                  <td className="celula-somente-leitura">{formatarMoeda(parcela.valor_apurado)}</td>
                  <td>
                    <select value={opcaoCorrecao(parcela)} onChange={(e) => trocarOpcaoCorrecao(parcela.id, e.target.value as OpcaoDefault)}>
                      <option value="default">{rotuloCorrecao}</option>
                      <option value="sem">Sem Correção Monetária</option>
                      <option value="personalizado">Personalizado…</option>
                    </select>
                  </td>
                  <td>
                    <select value={opcaoJuros(parcela)} onChange={(e) => trocarOpcaoJuros(parcela.id, e.target.value as OpcaoDefault)}>
                      <option value="default">{rotuloJuros}</option>
                      <option value="sem">Sem Juros</option>
                      <option value="personalizado">Personalizado…</option>
                    </select>
                  </td>
                  <td>
                    <input
                      placeholder="0"
                      value={percentualParaExibicao(parcela.multa_percentual)}
                      onChange={(e) =>
                        setParcelas((ps) =>
                          ps.map((p) => (p.id === parcela.id ? { ...p, multa_percentual: e.target.value ? String(Number(e.target.value) / 100) : null } : p))
                        )
                      }
                      onBlur={() => salvarParcela(parcela.id, { multa_percentual: parcelas.find((p) => p.id === parcela.id)?.multa_percentual ?? null })}
                    />
                  </td>
                  <td>
                    <button type="button" onClick={() => setExpandida(expandida === parcela.id ? null : parcela.id)}>
                      {expandida === parcela.id ? "fechar" : "editar"}
                    </button>
                    <button type="button" onClick={() => remover(parcela.id)}>
                      remover
                    </button>
                  </td>
                </tr>
                {expandida === parcela.id && (
                  <tr>
                    <td colSpan={10}>
                      <ParcelaDetalhe
                        parcela={parcela}
                        onSalvar={(patch) => salvarParcela(parcela.id, patch)}
                        onMudouPagamentos={recarregar}
                        validacao={validacao}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            <tr>
              <td>{parcelas.length + 1}</td>
              <td>
                <Campo nome="rascunho.vencimento" validacao={validacao} como="div">
                  <input type="date" value={rascunho.vencimento} onChange={(e) => setRascunho({ ...rascunho, vencimento: e.target.value })} />
                </Campo>
              </td>
              <td>
                <Campo nome="rascunho.historico" validacao={validacao} como="div">
                  <input placeholder="histórico" value={rascunho.historico} onChange={(e) => setRascunho({ ...rascunho, historico: e.target.value })} />
                </Campo>
              </td>
              <td>
                <Campo nome="rascunho.valor_bruto" validacao={validacao} como="div">
                  <input placeholder="0,00" value={rascunho.valor_bruto} onChange={(e) => setRascunho({ ...rascunho, valor_bruto: e.target.value })} />
                </Campo>
              </td>
              <td colSpan={5} />
              <td>
                <button type="button" onClick={adicionar}>
                  + adicionar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {modalSerie && processoId && (
        <PreenchimentoSerieModal
          processoId={processoId}
          rotuloCorrecaoDefault={rotuloCorrecao}
          rotuloJurosDefault={rotuloJuros}
          onGerado={recarregar}
          onFechar={() => setModalSerie(false)}
        />
      )}

      {modalSalarioMinimo && processoId && (
        <SalarioMinimoModal
          processoId={processoId}
          rotuloCorrecaoDefault={rotuloCorrecao}
          rotuloJurosDefault={rotuloJuros}
          onGerado={recarregar}
          onFechar={() => setModalSalarioMinimo(false)}
        />
      )}

      <div className="acoes-rodape">
        <button type="button" onClick={() => irParaPasso(1)}>
          ← voltar
        </button>
        <button type="button" className="primario" onClick={continuar}>
          Continuar →
        </button>
      </div>
    </div>
  );
}

function ParcelaDetalhe({
  parcela,
  onSalvar,
  onMudouPagamentos,
  validacao,
}: {
  parcela: Parcela;
  onSalvar: (patch: Partial<Parcela>) => void;
  onMudouPagamentos: () => void;
  validacao: Validacao;
}) {
  const personalizadaCorrecao = !parcela.usa_correcao_default;
  const personalizadaJuros = !parcela.usa_juros_default;

  return (
    <div className="parcela-detalhe">
      {personalizadaCorrecao && (
        <CorrecaoSegmentoEditor
          segmentos={parcela.correcao_segmentos_override}
          onChange={(segmentos) => onSalvar({ correcao_segmentos_override: segmentos })}
          validacao={validacao}
          prefixo={`parcela.${parcela.id}.correcao.`}
        />
      )}
      {personalizadaJuros && (
        <JurosSegmentoEditor
          segmentos={parcela.juros_segmentos_override}
          onChange={(segmentos) => onSalvar({ juros_segmentos_override: segmentos })}
          validacao={validacao}
          prefixo={`parcela.${parcela.id}.juros.`}
        />
      )}

      <h4>Deduções (Valor Pago)</h4>
      <PagamentoTable parcelaId={parcela.id} pagamentos={parcela.pagamentos} onMudou={onMudouPagamentos} />
    </div>
  );
}
