// "Artigo 523" do passo 3 (paridade SOSCálculos) — dois dropdowns fixos
// (Não/10%/15%/20%) para a multa e os honorários do art. 523 CPC, cada
// um virando (ou removendo) um Acessorio com base "saldo_remanescente_
// em_data_evento" (seção 3.9 — só existe se houve depósito parcial
// tempestivo). Exige uma "Data do evento" (fim do prazo de 15 dias).
import { useState } from "react";
import { api, mensagemDeErro } from "../../lib/api";
import type { Acessorio, TipoAcessorio } from "../../lib/types";

const OPCOES = ["Não", "10%", "15%", "20%"] as const;

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
}

function CampoArtigo523({ titulo, tipo, processoId, acessorio, dataEventoPadrao, onMudou }: CampoProps) {
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
      {acessorio && (
        <input type="date" value={acessorio.data_evento ?? ""} onChange={(e) => trocarData(e.target.value)} />
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
}

export function Artigo523Secao({ processoId, acessorios, dataEventoPadrao, onMudou }: Props) {
  const multa = acessorios.find((a) => a.tipo === "multa_523_cpc");
  const honorarios = acessorios.find((a) => a.tipo === "honorarios_523_cpc");

  return (
    <section className="secao-formulario">
      <h3>Artigo 523</h3>
      <div className="grade-formulario">
        <CampoArtigo523
          titulo="Multa art. 523"
          tipo="multa_523_cpc"
          processoId={processoId}
          acessorio={multa}
          dataEventoPadrao={dataEventoPadrao}
          onMudou={onMudou}
        />
        <CampoArtigo523
          titulo="Honorários art. 523"
          tipo="honorarios_523_cpc"
          processoId={processoId}
          acessorio={honorarios}
          dataEventoPadrao={dataEventoPadrao}
          onMudou={onMudou}
        />
      </div>
    </section>
  );
}
