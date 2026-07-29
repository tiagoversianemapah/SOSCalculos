import { useEffect, useState } from "react";
import { BackupPainel } from "../components/ui/BackupPainel";
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
      <h1>Cálculo Judicial</h1>
      <div className="cabecalho-lista">
        <button type="button" className="primario" onClick={onNovo}>
          + novo processo
        </button>
        <BackupPainel onRestaurado={recarregar} />
      </div>
      <table>
        <thead>
          <tr>
            <th>Número</th>
            <th>Requerente</th>
            <th>Requerido</th>
            <th>Data do cálculo</th>
            <th>Último total apurado</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {processos.map((p) => (
            <tr key={p.id}>
              <td>{p.numero_processo || "—"}</td>
              <td>{p.requerente}</td>
              <td>{p.requerido}</td>
              <td>{formatarData(p.data_calculo)}</td>
              <td>{formatarMoeda(p.ultimo_total_apurado)}</td>
              <td>
                <button type="button" onClick={() => onAbrir(p.id)}>
                  abrir
                </button>
              </td>
            </tr>
          ))}
          {processos.length === 0 && (
            <tr>
              <td colSpan={6}>Nenhum processo cadastrado ainda.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
