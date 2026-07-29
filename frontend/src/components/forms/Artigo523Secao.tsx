// "Artigo 523" do passo 3 (paridade SOSCálculos) — dois dropdowns fixos
// (Não/10%/15%/20%) para a multa e os honorários do art. 523 CPC, cada
// um virando (ou removendo) um Acessorio com base "saldo_remanescente_
// em_data_evento" (seção 3.9 — só existe se houve depósito parcial
// tempestivo). Exige uma "Data do evento" (fim do prazo de 15 dias).
import { useState } from "react";
import { api, mensagemDeErro } from "../../lib/api";
import type { Acessorio, TipoAcessorio } from "../../lib/types";
import { Campo, VALIDACAO_INERTE, obrigatorio, type RegraCampo, type Validacao } from "../../lib/validacao";
import { Icone } from "../ui/Icone";

const OPCOES = ["Não", "10%", "15%", "20%"] as const;

/** A "Data do evento" só existe na tela quando a opção não é "Não" — mas
 * quando existe é obrigatória (a base "saldo remanescente em data do
 * evento" não tem como ser calculada sem ela). */
export function regrasArtigo523(acessorios: Acessorio[]): RegraCampo[] {
  const regras: RegraCampo[] = [];
  for (const tipo of ["multa_523_cpc", "honorarios_523_cpc"] as const) {
    const acessorio = acessorios.find((a) => a.tipo === tipo);
    if (!acessorio) continue;
    regras.push(obrigatorio(`art523.${tipo}.data_evento`, acessorio.data_evento, "A data do evento"));
  }
  return regras;
}

function percentualDaOpcao(opcao: string): string | null {
  if (opcao === "Não") return null;
  return (Number(opcao.replace("%", "")) / 100).toString();
}

function opcaoDoAcessorio(a: Acessorio | undefined): string {
  if (!a || !a.percentual) return "Não";
  return `${Number(a.percentual) * 100}%`;
}

interface CampoProps {
  titulo: string;
  tipo: TipoAcessorio;
  processoId: string;
  acessorio: Acessorio | undefined;
  dataEventoPadrao: string;
  onMudou: () => void;
  validacao: Validacao;
}

function CampoArtigo523({
  titulo,
  tipo,
  processoId,
  acessorio,
  dataEventoPadrao,
  onMudou,
  validacao,
}: CampoProps) {
  const [erro, setErro] = useState<string | null>(null);

  const trocar = async (opcao: string) => {
    setErro(null);
    try {
      const percentual = percentualDaOpcao(opcao);
      if (percentual === null) {
        if (acessorio) await api.acessorios.remover(acessorio.id);
      } else if (acessorio) {
        await api.acessorios.atualizar(acessorio.id, { ...acessorio, percentual });
      } else {
        await api.acessorios.criar(processoId, {
          tipo,
          historico: titulo,
          base_calculo: "saldo_remanescente_em_data_evento",
          percentual,
          valor_fixo: null,
          data_evento: dataEventoPadrao || new Date().toISOString().slice(0, 10),
          usa_correcao_default: true,
          usa_juros_default: true,
        });
      }
      onMudou();
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  };

  const trocarData = async (data: string) => {
    if (!acessorio) return;
    await api.acessorios.atualizar(acessorio.id, { ...acessorio, data_evento: data });
    onMudou();
  };

  return (
    <label>
      {titulo}
      <select value={opcaoDoAcessorio(acessorio)} onChange={(e) => trocar(e.target.value)}>
        {OPCOES.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      {/* A data só entra na tela quando a opção deixa de ser "Não". */}
      {acessorio && (
        <Campo nome={`art523.${tipo}.data_evento`} validacao={validacao} como="div">
          <input type="date" value={acessorio.data_evento ?? ""} onChange={(e) => trocarData(e.target.value)} />
        </Campo>
      )}
      {erro && <span className="erro">{erro}</span>}
    </label>
  );
}

interface Props {
  processoId: string;
  acessorios: Acessorio[];
  dataEventoPadrao: string;
  onMudou: () => void;
  validacao?: Validacao;
}

export function Artigo523Secao({
  processoId,
  acessorios,
  dataEventoPadrao,
  onMudou,
  validacao = VALIDACAO_INERTE,
}: Props) {
  const multa = acessorios.find((a) => a.tipo === "multa_523_cpc");
  const honorarios = acessorios.find((a) => a.tipo === "honorarios_523_cpc");

  return (
    <section className="secao-formulario">
      <h3>
        <Icone nome="alerta" tamanho={16} />
        Artigo 523
      </h3>
      <div className="grade-formulario">
        <CampoArtigo523
          titulo="Multa art. 523"
          tipo="multa_523_cpc"
          processoId={processoId}
          acessorio={multa}
          dataEventoPadrao={dataEventoPadrao}
          onMudou={onMudou}
          validacao={validacao}
        />
        <CampoArtigo523
          titulo="Honorários art. 523"
          tipo="honorarios_523_cpc"
          processoId={processoId}
          acessorio={honorarios}
          dataEventoPadrao={dataEventoPadrao}
          onMudou={onMudou}
          validacao={validacao}
        />
      </div>
    </section>
  );
}
