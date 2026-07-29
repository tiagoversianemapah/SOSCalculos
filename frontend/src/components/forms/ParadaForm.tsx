import { useState } from "react";
import type { Parada } from "../../lib/types";

export type RascunhoParada = Omit<Parada, "id">;

function vazio(): RascunhoParada {
  return { data_inicio: "", data_fim: "", motivo: "", suspende_correcao: false, suspende_juros: false };
}

export function ParadaForm({ onCriar }: { onCriar: (dados: RascunhoParada) => void }) {
  const [form, setForm] = useState<RascunhoParada>(vazio());

  const enviar = () => {
    if (!form.data_inicio || !form.data_fim || !form.motivo) return;
    onCriar(form);
    setForm(vazio());
  };

  return (
    <div className="parada-form">
      <input type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} />
      <span>até</span>
      <input type="date" value={form.data_fim} onChange={(e) => setForm({ ...form, data_fim: e.target.value })} />
      <input placeholder="motivo (ex.: suspensão de exigibilidade)" value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} />
      <label>
        <input type="checkbox" checked={form.suspende_correcao} onChange={(e) => setForm({ ...form, suspende_correcao: e.target.checked })} />
        suspende correção
      </label>
      <label>
        <input type="checkbox" checked={form.suspende_juros} onChange={(e) => setForm({ ...form, suspende_juros: e.target.checked })} />
        suspende juros
      </label>
      <button type="button" onClick={enviar}>
        + adicionar parada
      </button>
    </div>
  );
}
