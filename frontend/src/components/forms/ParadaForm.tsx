import { useState } from "react";
import type { Parada } from "../../lib/types";
import { Campo, obrigatorio, useValidacao, type RegraCampo } from "../../lib/validacao";
import { Icone } from "../ui/Icone";

export type RascunhoParada = Omit<Parada, "id">;

function vazio(): RascunhoParada {
  return { data_inicio: "", data_fim: "", motivo: "", suspende_correcao: false, suspende_juros: false };
}

export function ParadaForm({ onCriar }: { onCriar: (dados: RascunhoParada) => void }) {
  const [form, setForm] = useState<RascunhoParada>(vazio());
  const validacao = useValidacao();

  const enviar = () => {
    const regras: RegraCampo[] = [
      obrigatorio("parada.data_inicio", form.data_inicio, "A data de início"),
      obrigatorio("parada.data_fim", form.data_fim, "A data final"),
      {
        nome: "parada.data_fim",
        valido: !form.data_inicio || !form.data_fim || form.data_fim >= form.data_inicio,
        mensagem: "A data final não pode ser anterior à inicial.",
      },
      obrigatorio("parada.motivo", form.motivo, "O motivo"),
      {
        nome: "parada.suspende",
        // Uma parada que não suspende nada não tem efeito no cálculo.
        valido: form.suspende_correcao || form.suspende_juros,
        mensagem: "Marque ao menos o que a parada suspende.",
      },
    ];
    if (!validacao.validar(regras)) return;
    onCriar(form);
    setForm(vazio());
    validacao.limparTudo();
  };

  return (
    <div className="parada-form">
      <Campo nome="parada.data_inicio" validacao={validacao} como="div">
        <input
          type="date"
          value={form.data_inicio}
          onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
        />
      </Campo>
      <span>até</span>
      <Campo nome="parada.data_fim" validacao={validacao} como="div">
        <input
          type="date"
          value={form.data_fim}
          onChange={(e) => setForm({ ...form, data_fim: e.target.value })}
        />
      </Campo>
      <Campo nome="parada.motivo" validacao={validacao} como="div" className="parada-motivo">
        <input
          placeholder="motivo (ex.: suspensão de exigibilidade)"
          value={form.motivo}
          onChange={(e) => setForm({ ...form, motivo: e.target.value })}
        />
      </Campo>
      <Campo nome="parada.suspende" validacao={validacao} como="div" className="parada-suspende">
        <div className="parada-caixas">
          <label className="caixa-inline">
            <input
              type="checkbox"
              checked={form.suspende_correcao}
              onChange={(e) => setForm({ ...form, suspende_correcao: e.target.checked })}
            />
            suspende correção
          </label>
          <label className="caixa-inline">
            <input
              type="checkbox"
              checked={form.suspende_juros}
              onChange={(e) => setForm({ ...form, suspende_juros: e.target.checked })}
            />
            suspende juros
          </label>
        </div>
      </Campo>
      <button type="button" onClick={enviar}>
        <Icone nome="mais" tamanho={14} />
        adicionar parada
      </button>
    </div>
  );
}
