// Sub-tabela de deduções (pagamento_parcial) de uma parcela — aba
// "créditos a deduzir" do SOSCálculos (seção 4, passo 2). Cada linha é
// persistida individualmente (rotas próprias, seção 4.5), diferente dos
// segmentos que são substituídos em bloco no PUT da parcela.
import { useState } from "react";
import { api } from "../../lib/api";
import { formatarData, formatarMoeda } from "../../lib/format";
import type { PagamentoParcial, TipoPagamentoParcial } from "../../lib/types";
import { TIPOS_PAGAMENTO } from "../../lib/types";

interface Props {
  parcelaId: string;
  pagamentos: PagamentoParcial[];
  onMudou: () => void;
}

function novoRascunho() {
  return { data: "", valor: "", tipo: "pagamento" as TipoPagamentoParcial, descricao: "" };
}

export function PagamentoTable({ parcelaId, pagamentos, onMudou }: Props) {
  const [rascunho, setRascunho] = useState(novoRascunho());
  const [salvando, setSalvando] = useState(false);

  const adicionar = async () => {
    if (!rascunho.data || !rascunho.valor) return;
    setSalvando(true);
    try {
      await api.pagamentos.criar(parcelaId, rascunho);
      setRascunho(novoRascunho());
      onMudou();
    } finally {
      setSalvando(false);
    }
  };

  const remover = async (id: string) => {
    await api.pagamentos.remover(id);
    onMudou();
  };

  return (
    <div className="tabela-pagamentos">
      <table>
        <thead>
          <tr>
            <th>Data</th>
            <th>Valor</th>
            <th>Tipo</th>
            <th>Descrição</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {pagamentos.map((p) => (
            <tr key={p.id}>
              <td>{formatarData(p.data)}</td>
              <td>{formatarMoeda(p.valor)}</td>
              <td>{TIPOS_PAGAMENTO.find((t) => t.value === p.tipo)?.label ?? p.tipo}</td>
              <td>{p.descricao ?? ""}</td>
              <td>
                <button type="button" onClick={() => remover(p.id)}>
                  remover
                </button>
              </td>
            </tr>
          ))}
          <tr>
            <td>
              <input type="date" value={rascunho.data} onChange={(e) => setRascunho({ ...rascunho, data: e.target.value })} />
            </td>
            <td>
              <input
                placeholder="0.00"
                value={rascunho.valor}
                onChange={(e) => setRascunho({ ...rascunho, valor: e.target.value })}
              />
            </td>
            <td>
              <select
                value={rascunho.tipo}
                onChange={(e) => setRascunho({ ...rascunho, tipo: e.target.value as TipoPagamentoParcial })}
              >
                {TIPOS_PAGAMENTO.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </td>
            <td>
              <input
                placeholder="descrição (opcional)"
                value={rascunho.descricao}
                onChange={(e) => setRascunho({ ...rascunho, descricao: e.target.value })}
              />
            </td>
            <td>
              <button type="button" disabled={salvando} onClick={adicionar}>
                + adicionar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
