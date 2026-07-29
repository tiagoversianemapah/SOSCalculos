// Formatação de EXIBIÇÃO apenas — proibido qualquer aritmética de
// negócio aqui (seção 6.2/12.1.2). decimal.js só evita que o
// JavaScript arredonde a string vinda da API antes de formatar.
import Decimal from "decimal.js";

export function formatarMoeda(valor: string | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  const numero = new Decimal(valor).toNumber();
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatarPercentual(valor: string | null | undefined, casas = 4): string {
  if (valor === null || valor === undefined) return "—";
  const percentual = new Decimal(valor).times(100);
  return `${percentual.toDecimalPlaces(casas).toString().replace(".", ",")}%`;
}

export function formatarData(valor: string | null | undefined): string {
  if (!valor) return "—";
  const [ano, mes, dia] = valor.split("-");
  return `${dia}/${mes}/${ano}`;
}

export function formatarCompetencia(valor: string | null | undefined): string {
  if (!valor) return "—";
  const [ano, mes] = valor.split("-");
  return `${mes}/${ano}`;
}
