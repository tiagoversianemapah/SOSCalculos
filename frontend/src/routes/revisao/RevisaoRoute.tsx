// Passo 4 — Revisão final (seção 4/8). Totalização separada por
// natureza é somada aqui em cima do resultado que o backend já calculou
// (não é uma regra de cálculo nova — só soma valores prontos para
// exibição, ver nota em lib/format.ts).
import Decimal from "decimal.js";
import { useEffect, useState } from "react";
import { api, mensagemDeErro } from "../../lib/api";
import { formatarMoeda } from "../../lib/format";
import type { Acessorio, CalculoPreview, Parcela, Processo, TipoAcessorio } from "../../lib/types";
import { useWizard } from "../../store/wizardStore";

const TIPOS_HONORARIOS: TipoAcessorio[] = [
  "honorarios_sucumbencia",
  "honorarios_523_cpc",
  "honorarios_contratuais",
  "honorarios_execucao",
];
const TIPOS_MULTA: TipoAcessorio[] = ["multa", "multa_523_cpc"];

function somar(valores: string[]): Decimal {
  return valores.reduce((acc, v) => acc.plus(new Decimal(v)), new Decimal(0));
}

export function RevisaoRoute() {
  const { processoId } = useWizard();
  const [processo, setProcesso] = useState<Processo | null>(null);
  const [parcelas, setParcelas] = useState<Parcela[]>([]);
  const [acessorios, setAcessorios] = useState<Acessorio[]>([]);
  const [preview, setPreview] = useState<CalculoPreview | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [emitindo, setEmitindo] = useState(false);

  useEffect(() => {
    if (!processoId) return;
    api.processos.obter(processoId).then(setProcesso);
    api.parcelas.listar(processoId).then(setParcelas);
    api.acessorios.listar(processoId).then(setAcessorios);
  }, [processoId]);

  const calcular = async () => {
    if (!processoId) return;
    setCalculando(true);
    setErro(null);
    try {
      setPreview(await api.processos.calcular(processoId));
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setCalculando(false);
    }
  };

  const emitirPdf = async () => {
    if (!processoId) return;
    setEmitindo(true);
    setErro(null);
    try {
      const blob = await api.processos.emitir(processoId);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      // reflete o valor_apurado atualizado pela emissão nas telas anteriores
      api.parcelas.listar(processoId).then(setParcelas);
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setEmitindo(false);
    }
  };

  if (!processo) return <p>Carregando…</p>;

  const principalOriginal = somar(parcelas.map((p) => p.valor_bruto));
  const deducoesPagamentos = somar(parcelas.flatMap((p) => p.pagamentos.map((pg) => pg.valor)));
  // Deduções do passo "Deduções" (paridade SOSCálculos) são subtraídas
  // do total geral do processo, não do saldo de uma parcela — somadas
  // à parte pra não entrar na identidade contábil da correção abaixo.
  const deducoesPasso4 = preview ? somar(preview.deducoes.map((r) => r.valor_apurado)) : new Decimal(0);
  const deducoes = deducoesPagamentos.plus(deducoesPasso4);

  // juros_mes é sempre o juro isolado daquele mês — soma direta é segura.
  // Correção NÃO pode ser "saldo_corrigido - saldo_inicio" somado mês a
  // mês: saldo_inicio já inclui juros acumulados de meses anteriores
  // (seção 3.3), então a subtração mistura grandezas diferentes e pode
  // até dar negativa por engano. Isola por diferença dos totais:
  // principal - deduções + correção + juros = total apurado.
  let juros = new Decimal(0);
  let totalParcelasApurado = new Decimal(0);
  if (preview) {
    for (const resultado of preview.parcelas) {
      totalParcelasApurado = totalParcelasApurado.plus(new Decimal(resultado.valor_apurado));
      for (const linha of resultado.memoria) {
        juros = juros.plus(new Decimal(linha.juros_mes));
      }
    }
  }
  const correcao = totalParcelasApurado.minus(principalOriginal).plus(deducoesPagamentos).minus(juros);

  const acessorioPorTipo = (tipos: TipoAcessorio[]) =>
    preview
      ? somar(
          preview.acessorios
            .filter((r) => tipos.includes(acessorios.find((a) => a.id === r.acessorio_id)?.tipo as TipoAcessorio))
            .map((r) => r.valor_apurado)
        )
      : new Decimal(0);

  const honorarios = acessorioPorTipo(TIPOS_HONORARIOS);
  const multas = acessorioPorTipo(TIPOS_MULTA);
  const custas = acessorioPorTipo(["custas_processuais"]);

  return (
    <div className="rota-revisao">
      <h2>Revisão final</h2>
      <div className="resumo-processo">
        <p>
          <strong>{processo.requerente}</strong> × <strong>{processo.requerido}</strong>
        </p>
        <p>
          {processo.numero_processo} — {processo.comarca}/{processo.vara}
        </p>
        <p>Data do cálculo: {processo.data_calculo}</p>
      </div>

      <button type="button" onClick={calcular} disabled={calculando} className="primario">
        {calculando ? "calculando…" : "Calcular"}
      </button>
      {erro && <p className="erro">{erro}</p>}

      {preview && (
        <>
          <h3>Totalização por natureza</h3>
          <table className="tabela-totalizacao">
            <tbody>
              <tr>
                <td>Principal original</td>
                <td>{formatarMoeda(principalOriginal.toString())}</td>
              </tr>
              <tr>
                <td>Correção monetária</td>
                <td>{formatarMoeda(correcao.toString())}</td>
              </tr>
              <tr>
                <td>Juros</td>
                <td>{formatarMoeda(juros.toString())}</td>
              </tr>
              <tr>
                <td>Honorários</td>
                <td>{formatarMoeda(honorarios.toString())}</td>
              </tr>
              <tr>
                <td>Multas</td>
                <td>{formatarMoeda(multas.toString())}</td>
              </tr>
              <tr>
                <td>Custas processuais</td>
                <td>{formatarMoeda(custas.toString())}</td>
              </tr>
              <tr>
                <td>(−) Deduções</td>
                <td>−{formatarMoeda(deducoes.toString())}</td>
              </tr>
              <tr className="linha-total">
                <td>Total geral</td>
                <td>{formatarMoeda(preview.total_geral)}</td>
              </tr>
            </tbody>
          </table>
        </>
      )}

      <p className="texto-auxiliar">
        Gerar o PDF cria uma nova execução de cálculo persistida — a memória fica gravada
        permanentemente para essa emissão, mesmo que os índices mudem depois.
      </p>
      <button type="button" onClick={emitirPdf} disabled={emitindo}>
        {emitindo ? "gerando…" : "Gerar PDF"}
      </button>
    </div>
  );
}
