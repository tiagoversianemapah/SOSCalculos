// Modal "Preenchimento em Série" do passo 2 (paridade SOSCálculos) —
// gera várias linhas de crédito (uma por mês) entre Data Inicial e
// Data Final, todas com o mesmo valor/histórico/configuração de
// correção-juros-multa. "Fim Mês?" usa o último dia de cada mês como
// vencimento em vez do dia de Data Inicial repetido.
import { useState } from "react";
import { api, mensagemDeErro } from "../../lib/api";
import { Campo, obrigatorio, useValidacao, type RegraCampo } from "../../lib/validacao";

interface Props {
  processoId: string;
  rotuloCorrecaoDefault: string;
  rotuloJurosDefault: string;
  onGerado: () => void;
  onFechar: () => void;
}

type OpcaoDefault = "default" | "sem";

function gerarVencimentos(inicio: string, fim: string, fimMes: boolean): string[] {
  const [anoIni, mesIni, diaIni] = inicio.split("-").map(Number);
  const [anoFim, mesFim] = fim.split("-").map(Number);
  const vencimentos: string[] = [];
  let ano = anoIni;
  let mes = mesIni;
  let guarda = 0;
  while ((ano < anoFim || (ano === anoFim && mes <= mesFim)) && guarda < 1200) {
    const ultimoDiaDoMes = new Date(ano, mes, 0).getDate();
    const dia = fimMes ? ultimoDiaDoMes : Math.min(diaIni, ultimoDiaDoMes);
    vencimentos.push(`${ano}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`);
    mes += 1;
    if (mes > 12) {
      mes = 1;
      ano += 1;
    }
    guarda += 1;
  }
  return vencimentos;
}

export function PreenchimentoSerieModal({
  processoId,
  rotuloCorrecaoDefault,
  rotuloJurosDefault,
  onGerado,
  onFechar,
}: Props) {
  const [dataInicial, setDataInicial] = useState("");
  const [dataFinal, setDataFinal] = useState("");
  const [valor, setValor] = useState("");
  const [percPago, setPercPago] = useState("");
  const [fimMes, setFimMes] = useState(false);
  const [correcao, setCorrecao] = useState<OpcaoDefault>("default");
  const [juros, setJuros] = useState<OpcaoDefault>("default");
  const [multaPercentual, setMultaPercentual] = useState("");
  const [historico, setHistorico] = useState("");
  const [gerando, setGerando] = useState(false);
  // Só falha de servidor — campo faltando aparece no próprio campo.
  const [erro, setErro] = useState<string | null>(null);
  const validacao = useValidacao();

  const gerar = async () => {
    const regras: RegraCampo[] = [
      obrigatorio("data_inicial", dataInicial, "A data inicial"),
      obrigatorio("data_final", dataFinal, "A data final"),
      {
        nome: "data_final",
        // Fim antes do início geraria zero parcelas em silêncio.
        valido: !dataInicial || !dataFinal || dataFinal >= dataInicial,
        mensagem: "A data final não pode ser anterior à inicial.",
      },
      {
        nome: "valor",
        valido: Boolean(valor && !Number.isNaN(Number(valor)) && Number(valor) > 0),
        mensagem: valor ? "Informe um valor numérico maior que zero." : "O valor é obrigatório.",
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
      obrigatorio("historico", historico, "O histórico"),
    ];
    if (!validacao.validar(regras)) return;
    setErro(null);
    setGerando(true);
    try {
      const vencimentos = gerarVencimentos(dataInicial, dataFinal, fimMes);
      const percPagoFracao = percPago ? Number(percPago) / 100 : 0;
      for (const vencimento of vencimentos) {
        const parcela = await api.parcelas.criar(processoId, {
          vencimento,
          historico,
          valor_bruto: valor,
          usa_correcao_default: correcao === "default",
          usa_juros_default: juros === "default",
          multa_percentual: multaPercentual ? String(Number(multaPercentual) / 100) : null,
        });
        if (percPagoFracao > 0) {
          const valorPago = (Number(valor) * percPagoFracao).toFixed(2);
          await api.pagamentos.criar(parcela.id, {
            data: vencimento,
            valor: valorPago,
            tipo: "pagamento",
            descricao: "% pago gerado pelo preenchimento em série",
          });
        }
      }
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
          <h3>Preenchimento Em Série</h3>
          <button type="button" onClick={onFechar} aria-label="Fechar">
            ✕
          </button>
        </div>
        {erro && <p className="erro">{erro}</p>}
        <div className="grade-formulario">
          <Campo nome="data_inicial" validacao={validacao} rotulo={<>Data Inicial *</>}>
            <input type="date" value={dataInicial} onChange={(e) => setDataInicial(e.target.value)} />
          </Campo>
          <Campo nome="data_final" validacao={validacao} rotulo={<>Data Final *</>}>
            <input type="date" value={dataFinal} onChange={(e) => setDataFinal(e.target.value)} />
          </Campo>
          <Campo nome="valor" validacao={validacao} rotulo={<>Valor *</>}>
            <input placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} />
          </Campo>
          <Campo
            nome="perc_pago"
            validacao={validacao}
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
          <input type="checkbox" id="fim-mes" checked={fimMes} onChange={(e) => setFimMes(e.target.checked)} />
          <label htmlFor="fim-mes">Fim Mês?</label>
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
            validacao={validacao}
            rotulo={
              <>
                Multa % <span className="campo-opcional">(opcional)</span>
              </>
            }
          >
            <input placeholder="0" value={multaPercentual} onChange={(e) => setMultaPercentual(e.target.value)} />
          </Campo>
        </div>
        <Campo nome="historico" validacao={validacao} className="campo-largo" rotulo={<>Histórico *</>}>
          <input value={historico} onChange={(e) => setHistorico(e.target.value)} />
        </Campo>
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
