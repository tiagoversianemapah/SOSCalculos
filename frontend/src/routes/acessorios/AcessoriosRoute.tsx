// Passo 3 — Acessórios e paradas extraordinárias, reestruturado em
// seções fixas (paridade SOSCálculos, ver especificacao-tecnica-motor-
// -calculo-judicial.md seção 0/4). "Diária (Data final)", "Diária
// (Competência)", "Salário Mínimo" e "Mensal" em Multas já confirmados
// via PDF real do SOSCálculos.
import { useEffect, useState } from "react";
import { AcessorioSecao, regrasAcessorios } from "../../components/forms/AcessorioSecao";
import { Artigo523Secao, regrasArtigo523 } from "../../components/forms/Artigo523Secao";
import { ParadaForm, type RascunhoParada } from "../../components/forms/ParadaForm";
import { Icone } from "../../components/ui/Icone";
import { api, mensagemDeErro } from "../../lib/api";
import { formatarData } from "../../lib/format";
import type { Acessorio, Parada, Processo } from "../../lib/types";
import { Campo, useValidacao } from "../../lib/validacao";
import { useWizard } from "../../store/wizardStore";

export function AcessoriosRoute() {
  const { processoId, irParaPasso } = useWizard();
  const [processo, setProcesso] = useState<Processo | null>(null);
  const [acessorios, setAcessorios] = useState<Acessorio[]>([]);
  const [paradas, setParadas] = useState<Parada[]>([]);
  // Só falha de servidor — campo faltando aparece no próprio campo.
  const [erro, setErro] = useState<string | null>(null);
  const validacao = useValidacao();

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

  // Os tipos desenhados por <AcessorioSecao> — os do art. 523 e os
  // honorários contratuais têm UI própria e regras próprias, então não
  // entram aqui (uma regra sem campo na tela não teria onde aparecer).
  const TIPOS_EM_SECAO = ["honorarios_sucumbencia", "honorarios_execucao", "multa", "custas_processuais"];

  const continuar = () => {
    setErro(null);
    const regras = [
      ...regrasArtigo523(acessorios),
      {
        nome: "honorarios_contratuais",
        // Opcional: em branco significa "sem honorários contratuais".
        valido:
          !honorariosContratuais?.percentual ||
          (!Number.isNaN(Number(honorariosContratuais.percentual)) &&
            Number(honorariosContratuais.percentual) > 0),
        mensagem: "Informe um percentual em fração (ex.: 0.10 = 10%) ou deixe em branco.",
      },
      ...regrasAcessorios(
        acessorios.filter((a) => TIPOS_EM_SECAO.includes(a.tipo)),
        processo
      ),
    ];
    if (!validacao.validar(regras)) return;
    irParaPasso(4);
  };

  return (
    <div className="rota-acessorios">
      <h2>
        <Icone nome="percentual" tamanho={20} />
        Acessórios
      </h2>
      <p className="texto-auxiliar">
        Neste passo, informe todos os acessórios necessários, como honorários, multas, custas, entre outros.
      </p>
      {erro && (
        <p className="erro">
          <Icone nome="alerta" />
          {erro}
        </p>
      )}

      <AcessorioSecao
        titulo="Honorários de Sucumbência"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="honorarios_sucumbencia"
        acessorios={acessoriosDoTipo("honorarios_sucumbencia")}
        subtiposPermitidos={["condenacao", "valor_monetario"]}
        onMudou={recarregar}
        validacao={validacao}
      />

      <Artigo523Secao
        processoId={processoId}
        acessorios={acessorios}
        dataEventoPadrao={processo.data_evento_padrao ?? ""}
        onMudou={recarregar}
        validacao={validacao}
      />

      <section className="secao-formulario">
        <h3>
          <Icone nome="percentual" tamanho={16} />
          Honorários Contratuais
        </h3>
        <Campo nome="honorarios_contratuais" validacao={validacao} rotulo="Percentual">
          <input
            placeholder="% (ex.: 0.10 = 10%)"
            defaultValue={honorariosContratuais?.percentual ?? ""}
            onBlur={(e) => salvarHonorariosContratuais(e.target.value)}
          />
        </Campo>
      </section>

      <AcessorioSecao
        titulo="Outros Honorários Execução"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="honorarios_execucao"
        acessorios={acessoriosDoTipo("honorarios_execucao")}
        subtiposPermitidos={["condenacao", "valor_monetario", "causa"]}
        onMudou={recarregar}
        validacao={validacao}
      />

      <AcessorioSecao
        titulo="Multas"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="multa"
        acessorios={acessoriosDoTipo("multa")}
        subtiposPermitidos={[
          "diaria_data_final",
          "diaria_competencia",
          "salario_minimo",
          "mensal",
          "valor_monetario",
          "condenacao",
          "causa",
        ]}
        onMudou={recarregar}
        validacao={validacao}
      />

      <AcessorioSecao
        titulo="Custas Processuais"
        processoId={processoId}
        processo={processo}
        tipoAcessorio="custas_processuais"
        acessorios={acessoriosDoTipo("custas_processuais")}
        subtiposPermitidos={["valor_monetario", "condenacao", "causa"]}
        onMudou={recarregar}
        validacao={validacao}
      />

      <section className="secao-formulario">
        <h3>
          <Icone nome="relogio" tamanho={16} />
          Paradas Extraordinárias
        </h3>
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
                <td className="celula-acoes">
                  <button
                    type="button"
                    className="icone-so"
                    aria-label="Remover parada"
                    title="Remover parada"
                    onClick={() => api.paradas.remover(p.id).then(recarregar)}
                  >
                    <Icone nome="lixeira" tamanho={14} />
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
          <Icone nome="seta-esquerda" />
          Voltar
        </button>
        <button type="button" className="primario" onClick={continuar}>
          Continuar
          <Icone nome="seta-direita" />
        </button>
      </div>
    </div>
  );
}
