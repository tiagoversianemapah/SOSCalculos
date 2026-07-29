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
import {
  Campo,
  VALIDACAO_INERTE,
  obrigatorio,
  type RegraCampo,
  type Validacao,
} from "../../lib/validacao";
import { CorrecaoSegmentoEditor, regrasCorrecao } from "./CorrecaoSegmentoEditor";
import { JurosSegmentoEditor, regrasJuros } from "./JurosSegmentoEditor";

export type Subtipo =
  | "condenacao"
  | "causa"
  | "valor_monetario"
  | "diaria_data_final"
  | "diaria_competencia"
  | "salario_minimo"
  | "mensal";

const ROTULO_SUBTIPO: Record<Subtipo, string> = {
  condenacao: "Sobre o Valor da Condenação",
  causa: "Sobre o Valor da Causa",
  valor_monetario: "Valor Monetário",
  diaria_data_final: "Diária (Data final)",
  diaria_competencia: "Diária (Competência)",
  salario_minimo: "Salário Mínimo",
  mensal: "Mensal",
};

const BASE_DO_SUBTIPO: Record<Subtipo, BaseCalculoAcessorio> = {
  condenacao: "total_liquido_parcelas",
  causa: "valor_da_causa",
  valor_monetario: "valor_fixo_absoluto",
  diaria_data_final: "valor_fixo_absoluto",
  diaria_competencia: "valor_fixo_absoluto",
  salario_minimo: "valor_fixo_absoluto",
  mensal: "valor_fixo_absoluto",
};

function subtipoDoAcessorio(a: Acessorio): Subtipo {
  if (a.valor_diario != null) return a.diaria_por_competencia ? "diaria_competencia" : "diaria_data_final";
  if (a.salario_minimo_quantidade != null) return "salario_minimo";
  if (a.valor_mensal != null) return "mensal";
  if (a.base_calculo === "valor_fixo_absoluto") return "valor_monetario";
  if (a.base_calculo === "valor_da_causa") return "causa";
  return "condenacao";
}

function regraNumero(nome: string, valor: string | null | undefined, rotulo: string): RegraCampo {
  if (!valor || !valor.trim()) return { nome, valido: false, mensagem: `${rotulo} é obrigatório.` };
  return {
    nome,
    valido: !Number.isNaN(Number(valor)) && Number(valor) > 0,
    mensagem: "Informe um número maior que zero.",
  };
}

/** Regras de todos os acessórios de uma tela — os campos cobrados mudam
 * conforme o "Tipo" escolhido na linha (é o mesmo `subtipoDoAcessorio`
 * que decide o que aparece no JSX, então os dois não saem de sincronia).
 * Campo de um subtipo que não está selecionado nunca é cobrado. */
export function regrasAcessorios(acessorios: Acessorio[], processo: Processo): RegraCampo[] {
  const regras: RegraCampo[] = [];
  for (const a of acessorios) {
    const chave = `acessorio.${a.id}`;
    const subtipo = subtipoDoAcessorio(a);
    if (subtipo === "condenacao" || subtipo === "causa") {
      regras.push(regraNumero(`${chave}.percentual`, a.percentual, "O percentual"));
      // "Sobre o Valor da Causa" depende de um campo de OUTRA tela (passo
      // 1) — sem ele o cálculo falha lá no fim, longe daqui.
      if (subtipo === "causa") {
        regras.push({
          nome: `${chave}.percentual`,
          valido: Boolean(processo.valor_causa && Number(processo.valor_causa) > 0),
          mensagem: 'Preencha o "Valor da Causa" no passo 1 para usar esta base.',
        });
      }
    } else if (subtipo === "valor_monetario") {
      regras.push(regraNumero(`${chave}.valor_fixo`, a.valor_fixo, "O valor"));
      regras.push(obrigatorio(`${chave}.data_evento`, a.data_evento, "A data"));
    } else if (subtipo === "diaria_data_final" || subtipo === "diaria_competencia") {
      regras.push(regraNumero(`${chave}.valor_diario`, a.valor_diario, "O valor diário"));
      regras.push(obrigatorio(`${chave}.data_inicio_acumulo`, a.data_inicio_acumulo, "A data de início"));
      regras.push(obrigatorio(`${chave}.data_evento`, a.data_evento, "A data final"));
      // Fim <= início daria zero dias e a multa sairia R$ 0,00 calada.
      if (a.data_inicio_acumulo && a.data_evento && a.data_evento <= a.data_inicio_acumulo) {
        regras.push({
          nome: `${chave}.data_evento`,
          valido: false,
          mensagem: "A data final tem que ser posterior à de início, senão a multa fica zerada.",
        });
      }
    } else if (subtipo === "salario_minimo") {
      regras.push(regraNumero(`${chave}.salario_minimo_quantidade`, a.salario_minimo_quantidade, "A quantidade"));
      regras.push(obrigatorio(`${chave}.data_evento`, a.data_evento, "A data do salário mínimo"));
    } else if (subtipo === "mensal") {
      regras.push(regraNumero(`${chave}.valor_mensal`, a.valor_mensal, "O valor mensal"));
      regras.push(obrigatorio(`${chave}.data_inicio_acumulo`, a.data_inicio_acumulo, "A data de início"));
      regras.push(obrigatorio(`${chave}.data_evento`, a.data_evento, "A data final"));
      // Menos de um mês entre as datas = nenhum lançamento = R$ 0,00.
      if (a.data_inicio_acumulo && a.data_evento && a.data_evento <= a.data_inicio_acumulo) {
        regras.push({
          nome: `${chave}.data_evento`,
          valido: false,
          mensagem: "A data final tem que ser pelo menos um mês depois da de início.",
        });
      }
    }
    // Segmentos próprios ficam escondidos atrás do "editar" — a seção se
    // abre sozinha quando algum deles reprova (ver useEffect na seção).
    if (!a.usa_correcao_default && a.correcao_segmentos_override.length > 0) {
      regras.push(...regrasCorrecao(`${chave}.correcao.`, a.correcao_segmentos_override));
    }
    if (!a.usa_juros_default && a.juros_segmentos_override.length > 0) {
      regras.push(...regrasJuros(`${chave}.juros.`, a.juros_segmentos_override));
    }
  }
  return regras;
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
  validacao?: Validacao;
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
  validacao = VALIDACAO_INERTE,
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

  // Se a validação reprovou um campo de segmento próprio (escondido
  // atrás do "editar"), abre a linha sozinha — só então o campo entra no
  // DOM e o `useValidacao` consegue rolar até ele.
  useEffect(() => {
    const chaveComErro = Object.keys(validacao.erros).find(
      (chave) => chave.includes(".correcao.") || chave.includes(".juros.")
    );
    if (!chaveComErro) return;
    const id = chaveComErro.split(".")[1];
    if (itens.some((item) => item.id === id)) setExpandido(id);
  }, [validacao.erros, itens]);

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
      const diaria = subtipo === "diaria_data_final" || subtipo === "diaria_competencia";
      const salarioMinimo = subtipo === "salario_minimo";
      const mensal = subtipo === "mensal";
      const usaDataEvento = monetario || diaria || salarioMinimo || mensal;
      const usaInicioAcumulo = diaria || mensal;
      await api.acessorios.criar(processoId, {
        tipo: tipoAcessorio,
        historico: "",
        base_calculo: BASE_DO_SUBTIPO[subtipo],
        percentual: usaDataEvento ? null : "0",
        valor_fixo: monetario ? "0" : null,
        data_evento: usaDataEvento ? hoje : null,
        valor_diario: diaria ? "0" : null,
        data_inicio_acumulo: usaInicioAcumulo ? hoje : null,
        diaria_por_competencia: subtipo === "diaria_competencia",
        salario_minimo_quantidade: salarioMinimo ? "1" : null,
        valor_mensal: mensal ? "0" : null,
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
        diaria_por_competencia: false,
        salario_minimo_quantidade: null,
        valor_mensal: null,
      });
    } else if (subtipo === "diaria_data_final" || subtipo === "diaria_competencia") {
      salvar(a.id, {
        base_calculo: "valor_fixo_absoluto",
        percentual: null,
        valor_fixo: null,
        valor_diario: a.valor_diario ?? "0",
        data_inicio_acumulo: a.data_inicio_acumulo ?? hoje,
        data_evento: a.data_evento ?? hoje,
        diaria_por_competencia: subtipo === "diaria_competencia",
        salario_minimo_quantidade: null,
        valor_mensal: null,
      });
    } else if (subtipo === "salario_minimo") {
      salvar(a.id, {
        base_calculo: "valor_fixo_absoluto",
        percentual: null,
        valor_fixo: null,
        valor_diario: null,
        data_inicio_acumulo: null,
        diaria_por_competencia: false,
        salario_minimo_quantidade: a.salario_minimo_quantidade ?? "1",
        data_evento: a.data_evento ?? hoje,
        valor_mensal: null,
      });
    } else if (subtipo === "mensal") {
      salvar(a.id, {
        base_calculo: "valor_fixo_absoluto",
        percentual: null,
        valor_fixo: null,
        valor_diario: null,
        diaria_por_competencia: false,
        salario_minimo_quantidade: null,
        valor_mensal: a.valor_mensal ?? "0",
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
        diaria_por_competencia: false,
        salario_minimo_quantidade: null,
        valor_mensal: null,
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
        const diaria = subtipo === "diaria_data_final" || subtipo === "diaria_competencia";
        const salarioMinimo = subtipo === "salario_minimo";
        const mensal = subtipo === "mensal";
        const temCorrecaoPropria = monetario || diaria || salarioMinimo || mensal;
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
              {!monetario && !diaria && !salarioMinimo && !mensal && (
                <Campo nome={`acessorio.${a.id}.percentual`} validacao={validacao} como="div">
                  <input
                    placeholder="% (ex.: 0.10 = 10%)"
                    defaultValue={a.percentual ?? ""}
                    onBlur={(e) => salvar(a.id, { percentual: e.target.value })}
                  />
                </Campo>
              )}
              {monetario && (
                <>
                  <Campo nome={`acessorio.${a.id}.valor_fixo`} validacao={validacao} como="div">
                    <input
                      placeholder="Valor"
                      defaultValue={a.valor_fixo ?? ""}
                      onBlur={(e) => salvar(a.id, { valor_fixo: e.target.value })}
                    />
                  </Campo>
                  <Campo nome={`acessorio.${a.id}.data_evento`} validacao={validacao} como="div">
                    <input
                      type="date"
                      value={a.data_evento ?? ""}
                      onChange={(e) => salvar(a.id, { data_evento: e.target.value || null })}
                    />
                  </Campo>
                </>
              )}
              {diaria && (
                <>
                  <Campo nome={`acessorio.${a.id}.valor_diario`} validacao={validacao} como="div">
                    <input
                      placeholder="Valor diário"
                      defaultValue={a.valor_diario ?? ""}
                      onBlur={(e) => salvar(a.id, { valor_diario: e.target.value })}
                    />
                  </Campo>
                  <Campo
                    nome={`acessorio.${a.id}.data_inicio_acumulo`}
                    validacao={validacao}
                    className="campo-inline-erro"
                    rotulo="Início"
                  >
                    <input
                      type="date"
                      value={a.data_inicio_acumulo ?? ""}
                      onChange={(e) => salvar(a.id, { data_inicio_acumulo: e.target.value || null })}
                    />
                  </Campo>
                  <Campo
                    nome={`acessorio.${a.id}.data_evento`}
                    validacao={validacao}
                    className="campo-inline-erro"
                    rotulo="Fim"
                  >
                    <input
                      type="date"
                      value={a.data_evento ?? ""}
                      onChange={(e) => salvar(a.id, { data_evento: e.target.value || null })}
                    />
                  </Campo>
                </>
              )}
              {salarioMinimo && (
                <>
                  <Campo nome={`acessorio.${a.id}.salario_minimo_quantidade`} validacao={validacao} como="div">
                    <input
                      placeholder="Quantidade"
                      defaultValue={a.salario_minimo_quantidade ?? ""}
                      onBlur={(e) => salvar(a.id, { salario_minimo_quantidade: e.target.value })}
                    />
                  </Campo>
                  <Campo
                    nome={`acessorio.${a.id}.data_evento`}
                    validacao={validacao}
                    className="campo-inline-erro"
                    rotulo="Data Salário Mínimo"
                  >
                    <input
                      type="date"
                      value={a.data_evento ?? ""}
                      onChange={(e) => salvar(a.id, { data_evento: e.target.value || null })}
                    />
                  </Campo>
                </>
              )}
              {mensal && (
                <>
                  <Campo nome={`acessorio.${a.id}.valor_mensal`} validacao={validacao} como="div">
                    <input
                      placeholder="Valor mensal"
                      defaultValue={a.valor_mensal ?? ""}
                      onBlur={(e) => salvar(a.id, { valor_mensal: e.target.value })}
                    />
                  </Campo>
                  <Campo
                    nome={`acessorio.${a.id}.data_inicio_acumulo`}
                    validacao={validacao}
                    className="campo-inline-erro"
                    rotulo="Início"
                  >
                    <input
                      type="date"
                      value={a.data_inicio_acumulo ?? ""}
                      onChange={(e) => salvar(a.id, { data_inicio_acumulo: e.target.value || null })}
                    />
                  </Campo>
                  <Campo
                    nome={`acessorio.${a.id}.data_evento`}
                    validacao={validacao}
                    className="campo-inline-erro"
                    rotulo="Fim"
                  >
                    <input
                      type="date"
                      value={a.data_evento ?? ""}
                      onChange={(e) => salvar(a.id, { data_evento: e.target.value || null })}
                    />
                  </Campo>
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
                    validacao={validacao}
                    prefixo={`acessorio.${a.id}.correcao.`}
                  />
                )}
                {temCorrecaoPropria && opcaoJuros(a) === "personalizado" && (
                  <JurosSegmentoEditor
                    segmentos={a.juros_segmentos_override}
                    onChange={(segmentos) => salvar(a.id, { juros_segmentos_override: segmentos })}
                    datasAncora={datasAncora}
                    validacao={validacao}
                    prefixo={`acessorio.${a.id}.juros.`}
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
