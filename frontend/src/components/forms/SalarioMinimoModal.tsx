// Modal "Salário Mínimo" do passo 2 (paridade SOSCálculos) — gera
// várias linhas de crédito (uma por mês) valendo um % do salário
// mínimo VIGENTE em cada competência. Diferente do "Preenchimento em
// Série" (valor fixo digitado), aqui o valor de cada linha depende de
// um cadastro manual do valor absoluto do salário mínimo por
// competência (ver app/models/salario_minimo_valor.py — deliberadamente
// não automatizado nem hardcoded no código, salário mínimo muda por
// decreto e um valor errado vai direto pra um documento judicial). Por
// isso a geração roda no backend (`gerarPorSalarioMinimo`), não aqui —
// o frontend nunca faz aritmética de negócio.
import { useEffect, useState } from "react";
import { api, mensagemDeErro } from "../../lib/api";
import { formatarMoeda } from "../../lib/format";
import type { SalarioMinimoValor } from "../../lib/types";
import { Icone } from "../ui/Icone";
import { Campo, obrigatorio, useValidacao, type RegraCampo } from "../../lib/validacao";

interface Props {
  processoId: string;
  rotuloCorrecaoDefault: string;
  rotuloJurosDefault: string;
  onGerado: () => void;
  onFechar: () => void;
}

type OpcaoDefault = "default" | "sem";

export function SalarioMinimoModal({
  processoId,
  rotuloCorrecaoDefault,
  rotuloJurosDefault,
  onGerado,
  onFechar,
}: Props) {
  const [valores, setValores] = useState<SalarioMinimoValor[]>([]);
  const [novaCompetencia, setNovaCompetencia] = useState("");
  const [novoValor, setNovoValor] = useState("");
  const [erroCadastro, setErroCadastro] = useState<string | null>(null);
  // Duas validações independentes: o cadastro de valores e o gerador de
  // linhas são formulários separados dentro do mesmo modal — um erro num
  // não pode marcar campo do outro.
  const validacaoCadastro = useValidacao();
  const validacaoGerador = useValidacao();

  const [dataInicial, setDataInicial] = useState("");
  const [dataFinal, setDataFinal] = useState("");
  const [percSalario, setPercSalario] = useState("");
  const [percPago, setPercPago] = useState("");
  const [fimMes, setFimMes] = useState(false);
  const [correcao, setCorrecao] = useState<OpcaoDefault>("default");
  const [juros, setJuros] = useState<OpcaoDefault>("default");
  const [multaPercentual, setMultaPercentual] = useState("");
  const [historico, setHistorico] = useState("");
  const [gerando, setGerando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const recarregarValores = () => api.salarioMinimo.listar().then(setValores);
  useEffect(() => {
    recarregarValores();
  }, []);

  const adicionarValor = async () => {
    setErroCadastro(null);
    const regras: RegraCampo[] = [
      obrigatorio("competencia", novaCompetencia, "A competência"),
      {
        nome: "novo_valor",
        valido: Boolean(novoValor && !Number.isNaN(Number(novoValor)) && Number(novoValor) > 0),
        mensagem: novoValor ? "Informe um valor numérico maior que zero." : "O valor é obrigatório.",
      },
      {
        nome: "competencia",
        // Cadastrar duas vezes a mesma competência estoura a UNIQUE lá no
        // banco, com uma mensagem que não diz qual campo é.
        valido: !valores.some((v) => v.competencia.slice(0, 7) === novaCompetencia),
        mensagem: "Essa competência já está cadastrada — remova a linha antiga antes.",
      },
    ];
    if (!validacaoCadastro.validar(regras)) return;
    try {
      await api.salarioMinimo.criar({ competencia: `${novaCompetencia}-01`, valor: novoValor });
      setNovaCompetencia("");
      setNovoValor("");
      recarregarValores();
    } catch (e) {
      setErroCadastro(mensagemDeErro(e));
    }
  };

  const removerValor = async (id: string) => {
    await api.salarioMinimo.remover(id);
    recarregarValores();
  };

  const gerar = async () => {
    const regras: RegraCampo[] = [
      obrigatorio("data_inicial", dataInicial, "A data inicial"),
      obrigatorio("data_final", dataFinal, "A data final"),
      {
        nome: "data_final",
        valido: !dataInicial || !dataFinal || dataFinal >= dataInicial,
        mensagem: "A data final não pode ser anterior à inicial.",
      },
      {
        nome: "perc_salario",
        valido: Boolean(percSalario && !Number.isNaN(Number(percSalario)) && Number(percSalario) > 0),
        mensagem: percSalario
          ? "Informe uma porcentagem maior que zero (ex.: 100 para um salário)."
          : "A porcentagem do salário é obrigatória.",
      },
      {
        nome: "perc_pago",
        valido: !percPago || (!Number.isNaN(Number(percPago)) && Number(percPago) >= 0 && Number(percPago) <= 100),
        mensagem: "Informe uma porcentagem entre 0 e 100.",
      },
      {
        nome: "multa_percentual",
        valido: !multaPercentual || !Number.isNaN(Number(multaPercentual)),
        mensagem: "Informe uma porcentagem (ex.: 10).",
      },
      {
        nome: "data_inicial",
        // Sem nenhum valor cadastrado o backend recusa tudo — melhor
        // dizer isso aqui do que deixar a geração falhar depois.
        valido: valores.length > 0,
        mensagem: "Cadastre ao menos um valor de salário mínimo acima antes de gerar.",
      },
      obrigatorio("historico", historico, "O histórico"),
    ];
    if (!validacaoGerador.validar(regras)) return;
    setErro(null);
    setGerando(true);
    try {
      await api.parcelas.gerarPorSalarioMinimo(processoId, {
        data_inicial: dataInicial,
        data_final: dataFinal,
        percentual_salario: String(Number(percSalario) / 100),
        percentual_pago: percPago ? String(Number(percPago) / 100) : null,
        fim_mes: fimMes,
        historico,
        usa_correcao_default: correcao === "default",
        usa_juros_default: juros === "default",
        multa_percentual: multaPercentual ? String(Number(multaPercentual) / 100) : null,
      });
      onGerado();
      onFechar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setGerando(false);
    }
  };

  return (
    <div className="modal-fundo" role="dialog" aria-modal="true">
      <div className="modal-caixa">
        <div className="modal-cabecalho">
          <h3>
            <Icone nome="dinheiro" tamanho={18} />
            Salário Mínimo
          </h3>
          <button type="button" className="icone-so neutro" onClick={onFechar} aria-label="Fechar">
            <Icone nome="fechar" tamanho={15} />
          </button>
        </div>

        <h4>Valores cadastrados</h4>
        <p className="texto-auxiliar">
          Cada valor vale a partir da competência cadastrada até o próximo cadastro — só precisa
          lançar quando o salário mínimo muda, não todo mês.
        </p>
        {erroCadastro && (
          <p className="erro">
            <Icone nome="alerta" />
            {erroCadastro}
          </p>
        )}
        {valores.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Competência</th>
                <th>Valor</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {valores.map((v) => (
                <tr key={v.id}>
                  <td>{v.competencia.slice(0, 7)}</td>
                  <td>{formatarMoeda(v.valor)}</td>
                  <td>
                    <button
                      type="button"
                      className="icone-so"
                      onClick={() => removerValor(v.id)}
                      aria-label="Remover valor"
                      title="Remover valor"
                    >
                      <Icone nome="lixeira" tamanho={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="grade-formulario">
          <Campo nome="competencia" validacao={validacaoCadastro} rotulo="Competência (mês/ano)">
            <input type="month" value={novaCompetencia} onChange={(e) => setNovaCompetencia(e.target.value)} />
          </Campo>
          <Campo nome="novo_valor" validacao={validacaoCadastro} rotulo="Valor (R$)">
            <input placeholder="0,00" value={novoValor} onChange={(e) => setNovoValor(e.target.value)} />
          </Campo>
        </div>
        <button type="button" className="adicionar" onClick={adicionarValor}>
          <Icone nome="mais" tamanho={14} />
          adicionar valor
        </button>

        <hr />

        <h4>Gerar linhas de crédito</h4>
        {erro && (
          <p className="erro">
            <Icone nome="alerta" />
            {erro}
          </p>
        )}
        <div className="grade-formulario">
          <Campo nome="data_inicial" validacao={validacaoGerador} rotulo={<>Data Inicial *</>}>
            <input type="date" value={dataInicial} onChange={(e) => setDataInicial(e.target.value)} />
          </Campo>
          <Campo nome="data_final" validacao={validacaoGerador} rotulo={<>Data Final *</>}>
            <input type="date" value={dataFinal} onChange={(e) => setDataFinal(e.target.value)} />
          </Campo>
          <Campo nome="perc_salario" validacao={validacaoGerador} rotulo={<>Perc. Salário (%) *</>}>
            <input placeholder="0" value={percSalario} onChange={(e) => setPercSalario(e.target.value)} />
          </Campo>
          <Campo
            nome="perc_pago"
            validacao={validacaoGerador}
            rotulo={
              <>
                % Pago <span className="campo-opcional">(opcional)</span>
              </>
            }
          >
            <input placeholder="0" value={percPago} onChange={(e) => setPercPago(e.target.value)} />
          </Campo>
        </div>
        <div className="linha-checkbox">
          <input type="checkbox" id="fim-mes-sm" checked={fimMes} onChange={(e) => setFimMes(e.target.checked)} />
          <label htmlFor="fim-mes-sm">Fim Mês?</label>
        </div>
        <div className="grade-formulario">
          <label>
            Correção Monetária
            <select value={correcao} onChange={(e) => setCorrecao(e.target.value as OpcaoDefault)}>
              <option value="default">{rotuloCorrecaoDefault}</option>
              <option value="sem">Sem Correção Monetária</option>
            </select>
          </label>
          <label>
            Juros
            <select value={juros} onChange={(e) => setJuros(e.target.value as OpcaoDefault)}>
              <option value="default">{rotuloJurosDefault}</option>
              <option value="sem">Sem Juros</option>
            </select>
          </label>
          <Campo
            nome="multa_percentual"
            validacao={validacaoGerador}
            rotulo={
              <>
                Multa % <span className="campo-opcional">(opcional)</span>
              </>
            }
          >
            <input placeholder="0" value={multaPercentual} onChange={(e) => setMultaPercentual(e.target.value)} />
          </Campo>
        </div>
        <Campo nome="historico" validacao={validacaoGerador} className="campo-largo" rotulo={<>Histórico *</>}>
          <input value={historico} onChange={(e) => setHistorico(e.target.value)} />
        </Campo>
        <div className="modal-rodape">
          <button type="button" className="primario" disabled={gerando} onClick={gerar}>
            <Icone nome="raio" />
            {gerando ? "Gerando…" : "Gerar"}
          </button>
          <button type="button" onClick={onFechar}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
