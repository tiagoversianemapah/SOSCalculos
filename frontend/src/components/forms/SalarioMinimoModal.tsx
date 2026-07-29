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
    if (!novaCompetencia || !novoValor) {
      setErroCadastro("Preencha a competência e o valor.");
      return;
    }
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
    if (!dataInicial || !dataFinal || !percSalario || !historico) {
      setErro("Preencha data inicial, data final, % do salário e histórico.");
      return;
    }
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
          <h3>Salário Mínimo</h3>
          <button type="button" onClick={onFechar} aria-label="Fechar">
            ✕
          </button>
        </div>

        <h4>Valores cadastrados</h4>
        <p className="texto-auxiliar">
          Cada valor vale a partir da competência cadastrada até o próximo cadastro — só precisa
          lançar quando o salário mínimo muda, não todo mês.
        </p>
        {erroCadastro && <p className="erro">{erroCadastro}</p>}
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
                    <button type="button" onClick={() => removerValor(v.id)}>
                      remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="grade-formulario">
          <label>
            Competência (mês/ano)
            <input type="month" value={novaCompetencia} onChange={(e) => setNovaCompetencia(e.target.value)} />
          </label>
          <label>
            Valor (R$)
            <input placeholder="0,00" value={novoValor} onChange={(e) => setNovoValor(e.target.value)} />
          </label>
        </div>
        <button type="button" onClick={adicionarValor}>
          + adicionar valor
        </button>

        <hr />

        <h4>Gerar linhas de crédito</h4>
        {erro && <p className="erro">{erro}</p>}
        <div className="grade-formulario">
          <label>
            Data Inicial *
            <input type="date" value={dataInicial} onChange={(e) => setDataInicial(e.target.value)} />
          </label>
          <label>
            Data Final *
            <input type="date" value={dataFinal} onChange={(e) => setDataFinal(e.target.value)} />
          </label>
          <label>
            Perc. Salário (%) *
            <input placeholder="0" value={percSalario} onChange={(e) => setPercSalario(e.target.value)} />
          </label>
          <label>
            % Pago <span className="campo-opcional">(opcional)</span>
            <input placeholder="0" value={percPago} onChange={(e) => setPercPago(e.target.value)} />
          </label>
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
          <label>
            Multa % <span className="campo-opcional">(opcional)</span>
            <input placeholder="0" value={multaPercentual} onChange={(e) => setMultaPercentual(e.target.value)} />
          </label>
        </div>
        <label className="campo-largo">
          Histórico *
          <input value={historico} onChange={(e) => setHistorico(e.target.value)} />
        </label>
        <div className="modal-rodape">
          <button type="button" className="primario" disabled={gerando} onClick={gerar}>
            {gerando ? "gerando…" : "Gerar"}
          </button>
          <button type="button" onClick={onFechar}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
