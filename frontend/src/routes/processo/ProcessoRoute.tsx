// Passo 1 — Cadastro do processo e configurações de correção/juros
// (paridade de campos com o SOSCálculos, ver especificacao-tecnica-
// -motor-calculo-judicial.md seção 0/2). Só Data do Cálculo, Requerente
// e Requerido são obrigatórios — o resto pode ficar em branco e o
// rascunho pode ser salvo incompleto.
import { useEffect, useState } from "react";
import { CorrecaoSegmentoEditor } from "../../components/forms/CorrecaoSegmentoEditor";
import { JurosSegmentoEditor } from "../../components/forms/JurosSegmentoEditor";
import { EditorRico } from "../../components/ui/EditorRico";
import { api, mensagemDeErro } from "../../lib/api";
import { PRESETS_CORRECAO, PRESETS_JUROS } from "../../lib/presets";
import type { CorrecaoSegmento, JurosSegmento, Processo, TipoVencimento } from "../../lib/types";
import { CAMPO_DATA_ANCORA, CONTAGENS_JUROS } from "../../lib/types";
import { useWizard } from "../../store/wizardStore";

type FormularioProcesso = Omit<Processo, "id">;

function formularioVazio(): FormularioProcesso {
  return {
    requerente: "",
    requerido: "",
    data_calculo: new Date().toISOString().slice(0, 10),
    numero_processo: "",
    comarca: "",
    vara: "",
    contrato: "",
    feito: "",
    observacoes: "",
    exibir_relatorio_detalhado: true,
    exibir_relatorio_correcao: false,
    contagem_juros: "pro_rata",
    configura_deducoes: false,
    aplicar_art_354_cc: false,
    valor_causa: "",
    correcao_segmentos_default: [],
    juros_segmentos_default: [],
  };
}

function agruparPorCategoria<T extends { categoria: string }>(itens: T[]): Map<string, T[]> {
  const mapa = new Map<string, T[]>();
  for (const item of itens) {
    const grupo = mapa.get(item.categoria) ?? [];
    grupo.push(item);
    mapa.set(item.categoria, grupo);
  }
  return mapa;
}

export function ProcessoRoute() {
  const { processoId, definirProcessoId, definirConfiguraDeducoes, irParaPasso } = useWizard();
  const [form, setForm] = useState<FormularioProcesso>(formularioVazio());
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!processoId) return;
    api.processos.obter(processoId).then(setForm);
  }, [processoId]);

  const campo = <K extends keyof FormularioProcesso>(chave: K, valor: FormularioProcesso[K]) =>
    setForm((atual) => ({ ...atual, [chave]: valor }));

  const datasAncora: Partial<Record<TipoVencimento, string | null | undefined>> = Object.fromEntries(
    Object.entries(CAMPO_DATA_ANCORA).map(([tipo, campoProcesso]) => [
      tipo,
      form[campoProcesso as keyof FormularioProcesso],
    ])
  );

  const escolherPresetCorrecao = (chave: string) => {
    const preset = PRESETS_CORRECAO.find((p) => p.chave === chave);
    if (!preset) return;
    const atual = form.correcao_segmentos_default;
    const primeiro = preset.aplicar(1);
    campo(
      "correcao_segmentos_default",
      atual.length === 0 ? [primeiro] : [primeiro, ...atual.slice(1)]
    );
  };

  const escolherPresetJuros = (chave: string) => {
    const preset = PRESETS_JUROS.find((p) => p.chave === chave);
    if (!preset) return;
    const atual = form.juros_segmentos_default;
    const primeiro = preset.aplicar(1);
    campo("juros_segmentos_default", atual.length === 0 ? [primeiro] : [primeiro, ...atual.slice(1)]);
  };

  // "required"/"*" na UI não bloqueiam nada sozinhos — são <input> soltos
  // dentro de <button type="button" onClick>, não um <form onSubmit>, então
  // o HTML5 nunca valida isso. "Salvar rascunho" continua permissivo (a
  // especificação permite rascunho incompleto); só "Salvar e Avançar" checa.
  const camposFaltando = (): string[] => {
    const faltando: string[] = [];
    if (!form.requerente.trim()) faltando.push("Requerente");
    if (!form.requerido.trim()) faltando.push("Requerido");
    if (!form.data_calculo) faltando.push("Data Cálculo");
    if (form.correcao_segmentos_default.length === 0) faltando.push("Tabela Correção");
    if (form.juros_segmentos_default.length === 0) faltando.push("Taxa de Juros");
    return faltando;
  };

  const salvar = async (avancar: boolean) => {
    setErro(null);
    if (avancar) {
      const faltando = camposFaltando();
      if (faltando.length > 0) {
        setErro(`Preencha antes de avançar: ${faltando.join(", ")}.`);
        return;
      }
    }
    setSalvando(true);
    try {
      const dados = { ...form, valor_causa: form.valor_causa || null };
      const salvo = processoId
        ? await api.processos.atualizar(processoId, dados)
        : await api.processos.criar(dados);
      definirProcessoId(salvo.id);
      definirConfiguraDeducoes(salvo.configura_deducoes);
      if (avancar) irParaPasso(2);
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setSalvando(false);
    }
  };

  const presetsCorrecaoAgrupados = agruparPorCategoria(PRESETS_CORRECAO);
  const presetsJurosAgrupados = agruparPorCategoria(PRESETS_JUROS);

  return (
    <div className="rota-processo">
      <h2>Liquidação de Sentença — Cálculo Judicial (Passo 1)</h2>
      <p className="texto-auxiliar">
        Informe o cadastro básico e as configurações de correção monetária e de juros para a
        liquidação de sentença.
      </p>
      {erro && <p className="erro">{erro}</p>}

      <section className="secao-formulario">
        <h3>Cadastro</h3>
        <div className="grade-formulario">
          <label>
            Data Cálculo *
            <input type="date" value={form.data_calculo} onChange={(e) => campo("data_calculo", e.target.value)} required />
          </label>
          <label>
            Processo <span className="campo-opcional">(opcional)</span>
            <input value={form.numero_processo ?? ""} onChange={(e) => campo("numero_processo", e.target.value)} />
          </label>
          <label>
            Requerente *
            <input value={form.requerente} onChange={(e) => campo("requerente", e.target.value)} required />
          </label>
          <label>
            Requerido *
            <input value={form.requerido} onChange={(e) => campo("requerido", e.target.value)} required />
          </label>
          <label>
            Contrato <span className="campo-opcional">(opcional)</span>
            <input value={form.contrato ?? ""} onChange={(e) => campo("contrato", e.target.value)} />
          </label>
          <label>
            Comarca <span className="campo-opcional">(opcional)</span>
            <input value={form.comarca ?? ""} onChange={(e) => campo("comarca", e.target.value)} />
          </label>
          <label>
            Vara <span className="campo-opcional">(opcional)</span>
            <input value={form.vara ?? ""} onChange={(e) => campo("vara", e.target.value)} />
          </label>
          <label>
            Feito <span className="campo-opcional">(opcional)</span>
            <input
              placeholder="Informe ou comece a digitar para buscar..."
              value={form.feito ?? ""}
              onChange={(e) => campo("feito", e.target.value)}
            />
          </label>
          <label>
            Valor da Causa <span className="campo-opcional">(opcional — usado pelos acessórios "Sobre o Valor da Causa" no passo 3)</span>
            <input
              placeholder="0,00"
              value={form.valor_causa ?? ""}
              onChange={(e) => campo("valor_causa", e.target.value)}
            />
          </label>
        </div>
        <label className="campo-largo">
          Observações <span className="campo-opcional">(opcional)</span>
          <EditorRico valor={form.observacoes ?? ""} onChange={(html) => campo("observacoes", html)} />
        </label>
        <div className="linha-checkbox">
          <input
            type="checkbox"
            id="exibir-relatorio-detalhado"
            checked={form.exibir_relatorio_detalhado}
            onChange={(e) => campo("exibir_relatorio_detalhado", e.target.checked)}
          />
          <label htmlFor="exibir-relatorio-detalhado">Exibir relatório detalhado</label>
        </div>
      </section>

      <section className="secao-formulario">
        <h3>Configurações de Correção Monetária</h3>
        <div className="preset-selector">
          <label>
            Tabela Correção *
            <select defaultValue="" onChange={(e) => e.target.value && escolherPresetCorrecao(e.target.value)}>
              <option value="" disabled>
                Selecione…
              </option>
              {[...presetsCorrecaoAgrupados.entries()].map(([categoria, presets]) => (
                <optgroup key={categoria} label={categoria}>
                  {presets.map((preset) => (
                    <option key={preset.chave} value={preset.chave}>
                      {preset.rotulo}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <span className="texto-auxiliar">
            Escolher aqui preenche a primeira tabela abaixo — ajuste as datas e adicione outras
            tabelas se precisar compor mais de um período.
          </span>
        </div>
        <CorrecaoSegmentoEditor
          segmentos={form.correcao_segmentos_default}
          onChange={(segmentos: CorrecaoSegmento[]) => campo("correcao_segmentos_default", segmentos)}
          datasAncora={datasAncora}
        />
        <div className="linha-checkbox">
          <input
            type="checkbox"
            id="exibir-relatorio-correcao"
            checked={form.exibir_relatorio_correcao}
            onChange={(e) => campo("exibir_relatorio_correcao", e.target.checked)}
          />
          <label htmlFor="exibir-relatorio-correcao">Exibir relatório de Correção Monetária</label>
        </div>
      </section>

      <section className="secao-formulario">
        <h3>Configurações de Juros Moratórios</h3>
        <label>
          Contagem Juros
          <select value={form.contagem_juros} onChange={(e) => campo("contagem_juros", e.target.value as FormularioProcesso["contagem_juros"])}>
            {CONTAGENS_JUROS.map((opcao) => (
              <option key={opcao.value} value={opcao.value}>
                {opcao.label}
              </option>
            ))}
          </select>
        </label>
        <div className="preset-selector">
          <label>
            Taxa de Juros *
            <select defaultValue="" onChange={(e) => e.target.value && escolherPresetJuros(e.target.value)}>
              <option value="" disabled>
                Selecione…
              </option>
              {[...presetsJurosAgrupados.entries()].map(([categoria, presets]) => (
                <optgroup key={categoria} label={categoria}>
                  {presets.map((preset) => (
                    <option key={preset.chave} value={preset.chave}>
                      {preset.rotulo}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
        </div>
        <JurosSegmentoEditor
          segmentos={form.juros_segmentos_default}
          onChange={(segmentos: JurosSegmento[]) => campo("juros_segmentos_default", segmentos)}
          datasAncora={datasAncora}
        />
      </section>

      <section className="secao-formulario">
        <h3>Configurações</h3>
        <div className="grade-formulario">
          <label>
            Configurar Deduções
            <select
              value={form.configura_deducoes ? "sim" : "nao"}
              onChange={(e) => campo("configura_deducoes", e.target.value === "sim")}
            >
              <option value="nao">Não</option>
              <option value="sim">Sim</option>
            </select>
          </label>
          {form.configura_deducoes && (
            <label>
              Aplicar Art. 354 do CC
              <select
                value={form.aplicar_art_354_cc ? "sim" : "nao"}
                onChange={(e) => campo("aplicar_art_354_cc", e.target.value === "sim")}
              >
                <option value="nao">Não</option>
                <option value="sim">Sim</option>
              </select>
            </label>
          )}
        </div>
        <p className="texto-auxiliar">
          "Configurar Deduções" adiciona um passo extra pra lançar deduções com correção/juros
          próprios. "Aplicar Art. 354 do CC" faz cada pagamento abater primeiro os juros já
          vencidos e só depois o principal (Código Civil, art. 354) — o padrão (Não) abate o
          principal diretamente.
        </p>
      </section>

      <div className="acoes-rodape">
        <button type="button" disabled={salvando} onClick={() => salvar(false)}>
          Salvar rascunho
        </button>
        <button type="button" disabled={salvando} onClick={() => salvar(true)} className="primario">
          Salvar e Avançar →
        </button>
      </div>
    </div>
  );
}
