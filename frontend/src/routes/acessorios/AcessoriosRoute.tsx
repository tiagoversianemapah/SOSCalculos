// Passo 3 — Acessórios e paradas extraordinárias, reestruturado em
// seções fixas (paridade SOSCálculos, ver especificacao-tecnica-motor-
// -calculo-judicial.md seção 0/4). "Diária (Data final)", "Diária
// (Competência)", "Mensal" e "Salário Mínimo" em Multas ficam
// desabilitados por enquanto — fórmula de acréscimo ainda não
// confirmada (ver seção 11 e pendência registrada com o usuário).
import { useEffect, useState } from "react";
import { AcessorioSecao } from "../../components/forms/AcessorioSecao";
import { Artigo523Secao } from "../../components/forms/Artigo523Secao";
import { ParadaForm, type RascunhoParada } from "../../components/forms/ParadaForm";
import { api, mensagemDeErro } from "../../lib/api";
import { formatarData } from "../../lib/format";
import type { Acessorio, Parada, Processo } from "../../lib/types";
import { useWizard } from "../../store/wizardStore";

const MULTAS_DESABILITADAS = [
  { subtipo: "diaria_competencia", rotulo: "Diária (Competência)" },
  { subtipo: "mensal", rotulo: "Mensal" },
  { subtipo: "salario_minimo", rotulo: "Salário Mínimo" },
];

export function AcessoriosRoute() {
  const { processoId, irParaPasso } = useWizard();
  const [processo, setProcesso] = useState<Processo | null>(null);
  const [acessorios, setAcessorios] = useState<Acessorio[]>([]);
  const [paradas, setParadas] = useState<Parada[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = () => {
    if (!processoId) return;
    api.processos.obter(processoId).then(setProcesso);
    api.acessorios.listar(processoId).then(setAcessorios);
    api.paradas.listar(processoId).then(setParadas);
  };

  useEffect(recarregar, [processoId]);

  const criarParada = async (dados: RascunhoParada) => {
    if (!processoId) return;
    await api.paradas.criar(processoId, dados);
    recarregar();
  };

  const salvarHonorariosContratuais = async (percentual: string) => {
    if (!processoId) return;
    setErro(null);
    try {
      const existente = acessorios.find((a) => a.tipo === "honorarios_contratuais");
      if (existente) {
        await api.acessorios.atualizar(existente.id, { ...existente, percentual });
      } else if (percentual) {
        await api.acessorios.criar(processoId, {
          tipo: "honorarios_contratuais",
          historico: "Honorários contratuais",
          base_calculo: "total_liquido_parcelas",
          percentual,
          valor_fixo: null,
          usa_correcao_default: true,
          usa_juros_default: true,
        });
      }
      recarregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  if (!processoId || !processo) return <p>Carregando…</p>;

  const acessoriosDoTipo = (tipo: string) => acessorios.filter((a) => a.tipo === tipo);
  const honorariosContratuais = acessorios.find((a) => a.tipo === "honorarios_contratuais");

  return (
    <div className="rota-acessorios">
      <h2>Liquidação de Sentença — Cálculo Judicial (Passo 3)</h2>
      <p className="texto-auxiliar">
        Neste passo, informe todos os acessórios necessários, como honorários, multas, custas, entre outros.
      </p>
      {erro && <p className="erro">{erro}</p>}

      <AcessorioSecao
        titulo="Honorários de Sucumbência"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="honorarios_sucumbencia"
        acessorios={acessoriosDoTipo("honorarios_sucumbencia")}
        subtiposPermitidos={["condenacao", "valor_monetario"]}
        onMudou={recarregar}
      />

      <Artigo523Secao
        processoId={processoId}
        acessorios={acessorios}
        dataEventoPadrao={processo.data_evento_padrao ?? ""}
        onMudou={recarregar}
      />

      <section className="secao-formulario">
        <h3>Honorários Contratuais</h3>
        <label>
          Percentual
          <input
            placeholder="% (ex.: 0.10 = 10%)"
            defaultValue={honorariosContratuais?.percentual ?? ""}
            onBlur={(e) => salvarHonorariosContratuais(e.target.value)}
          />
        </label>
      </section>

      <AcessorioSecao
        titulo="Outros Honorários Execução"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="honorarios_execucao"
        acessorios={acessoriosDoTipo("honorarios_execucao")}
        subtiposPermitidos={["condenacao", "valor_monetario", "causa"]}
        onMudou={recarregar}
      />

      <AcessorioSecao
        titulo="Multas"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="multa"
        acessorios={acessoriosDoTipo("multa")}
        subtiposPermitidos={["diaria_data_final", "valor_monetario", "condenacao", "causa"]}
        subtiposDesabilitados={MULTAS_DESABILITADAS}
        onMudou={recarregar}
      />

      <AcessorioSecao
        titulo="Custas Processuais"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="custas_processuais"
        acessorios={acessoriosDoTipo("custas_processuais")}
        subtiposPermitidos={["valor_monetario", "condenacao", "causa"]}
        onMudou={recarregar}
      />

      <section className="secao-formulario">
        <h3>Paradas Extraordinárias</h3>
        <table>
          <thead>
            <tr>
              <th>Início</th>
              <th>Fim</th>
              <th>Motivo</th>
              <th>Suspende</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {paradas.map((p) => (
              <tr key={p.id}>
                <td>{formatarData(p.data_inicio)}</td>
                <td>{formatarData(p.data_fim)}</td>
                <td>{p.motivo}</td>
                <td>
                  {[p.suspende_correcao && "correção", p.suspende_juros && "juros"].filter(Boolean).join(" e ")}
                </td>
                <td>
                  <button type="button" onClick={() => api.paradas.remover(p.id).then(recarregar)}>
                    remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <ParadaForm onCriar={criarParada} />
      </section>

      <div className="acoes-rodape">
        <button type="button" onClick={() => irParaPasso(2)}>
          ← voltar
        </button>
        <button type="button" className="primario" onClick={() => irParaPasso(4)}>
          Continuar →
        </button>
      </div>
    </div>
  );
}
