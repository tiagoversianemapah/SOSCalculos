import { useEffect, useState } from "react";
import { BackupPainel } from "../components/ui/BackupPainel";
import { Icone } from "../components/ui/Icone";
import { api } from "../lib/api";
import { formatarData, formatarMoeda } from "../lib/format";
import type { ProcessoListItem } from "../lib/types";

export function ListaProcessos({ onAbrir, onNovo }: { onAbrir: (id: string) => void; onNovo: () => void }) {
  const [processos, setProcessos] = useState<ProcessoListItem[]>([]);

  const recarregar = () => {
    api.processos.listar().then(setProcessos);
  };

  useEffect(recarregar, []);

  return (
    <div className="lista-processos">
      <h1>Meus processos</h1>
      <p className="lista-subtitulo">
        {processos.length === 0
          ? "Nenhum cálculo cadastrado ainda."
          : `${processos.length} ${processos.length === 1 ? "cálculo cadastrado" : "cálculos cadastrados"}.`}
      </p>

      <div className="cabecalho-lista">
        <button type="button" className="primario" onClick={onNovo}>
          <Icone nome="mais" />
          Novo processo
        </button>
        <BackupPainel onRestaurado={recarregar} />
      </div>

      <div className="cartao">
        {processos.length === 0 ? (
          <div className="lista-vazia">
            <Icone nome="pasta" tamanho={40} />
            <p>Comece pelo primeiro cálculo</p>
            <span className="texto-auxiliar">
              Clique em "Novo processo" para cadastrar as partes e configurar correção e juros.
            </span>
          </div>
        ) : (
          <table className="tabela-processos">
            <thead>
              <tr>
                <th>Partes</th>
                <th>Número</th>
                <th>Data do cálculo</th>
                <th>Último total apurado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {processos.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div className="processo-partes">
                      {p.requerente || "—"} <span className="separador">×</span> {p.requerido || "—"}
                    </div>
                  </td>
                  <td>
                    <span className="processo-numero">{p.numero_processo || "—"}</span>
                  </td>
                  <td>{formatarData(p.data_calculo)}</td>
                  <td>
                    {p.ultimo_total_apurado ? (
                      <span className="valor-destaque">{formatarMoeda(p.ultimo_total_apurado)}</span>
                    ) : (
                      <span className="texto-auxiliar">não calculado</span>
                    )}
                  </td>
                  <td className="celula-acoes">
                    <button type="button" onClick={() => onAbrir(p.id)}>
                      Abrir
                      <Icone nome="seta-direita" tamanho={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
