// Cliente HTTP — base SEMPRE relativa (/api/v1), nunca host/porta
// absolutos (invariante 12.1.3/seção 4.5): o mesmo build funciona
// servido pelo FastAPI local ou, no futuro, por um servidor remoto.
import type {
  Acessorio,
  CalculoPreview,
  Deducao,
  GerarPorSalarioMinimoRequest,
  PagamentoParcial,
  Parada,
  Parcela,
  Processo,
  ProcessoListItem,
  SalarioMinimoValor,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

interface ErroValidacaoPydantic {
  loc?: unknown[];
  msg?: string;
}

function ehErroValidacaoPydantic(item: unknown): item is ErroValidacaoPydantic {
  return typeof item === "object" && item !== null && "msg" in item;
}

// FastAPI devolve `detail` como string (erro simples, ex.: 404/422 de
// negócio) OU como lista de erros de validação do Pydantic (422 de
// schema) — sem tratar os dois formatos, `String(detail)` num array de
// objetos vira "[object Object],[object Object]" pro usuário.
export function mensagemDeErro(e: unknown): string {
  if (e instanceof ApiError) {
    const { detail } = e;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (ehErroValidacaoPydantic(item)) {
            const caminho = Array.isArray(item.loc)
              ? item.loc.filter((parte) => parte !== "body").join(".")
              : "";
            return caminho ? `${caminho}: ${item.msg}` : String(item.msg ?? item);
          }
          return typeof item === "string" ? item : JSON.stringify(item);
        })
        .join("; ");
    }
    return e.message;
  }
  if (e instanceof Error) return e.message;
  return "Erro desconhecido.";
}

async function requisitar<T>(metodo: string, caminho: string, corpo?: unknown): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`, {
    method: metodo,
    headers: corpo !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
  });

  if (!resposta.ok) {
    let detail: unknown;
    try {
      detail = (await resposta.json()).detail;
    } catch {
      detail = resposta.statusText;
    }
    throw new ApiError(resposta.status, detail);
  }

  if (resposta.status === 204) {
    return undefined as T;
  }
  return (await resposta.json()) as T;
}

export const api = {
  processos: {
    listar: () => requisitar<ProcessoListItem[]>("GET", "/processos"),
    obter: (id: string) => requisitar<Processo>("GET", `/processos/${id}`),
    criar: (dados: Partial<Processo>) => requisitar<Processo>("POST", "/processos", dados),
    atualizar: (id: string, dados: Partial<Processo>) =>
      requisitar<Processo>("PUT", `/processos/${id}`, dados),
    remover: (id: string) => requisitar<void>("DELETE", `/processos/${id}`),
    calcular: (id: string) => requisitar<CalculoPreview>("POST", `/processos/${id}/calcular`),
    emitir: async (id: string): Promise<Blob> => {
      const resposta = await fetch(`${BASE}/processos/${id}/emitir`, { method: "POST" });
      if (!resposta.ok) {
        let detail: unknown;
        try {
          detail = (await resposta.json()).detail;
        } catch {
          detail = resposta.statusText;
        }
        throw new ApiError(resposta.status, detail);
      }
      return resposta.blob();
    },
  },
  parcelas: {
    listar: (processoId: string) => requisitar<Parcela[]>("GET", `/processos/${processoId}/parcelas`),
    criar: (processoId: string, dados: Partial<Parcela>) =>
      requisitar<Parcela>("POST", `/processos/${processoId}/parcelas`, dados),
    atualizar: (id: string, dados: Partial<Parcela>) =>
      requisitar<Parcela>("PUT", `/parcelas/${id}`, dados),
    remover: (id: string) => requisitar<void>("DELETE", `/parcelas/${id}`),
    gerarPorSalarioMinimo: (processoId: string, dados: GerarPorSalarioMinimoRequest) =>
      requisitar<Parcela[]>("POST", `/processos/${processoId}/parcelas/gerar-por-salario-minimo`, dados),
  },
  salarioMinimo: {
    listar: () => requisitar<SalarioMinimoValor[]>("GET", "/indices/salario-minimo"),
    criar: (dados: { competencia: string; valor: string }) =>
      requisitar<SalarioMinimoValor>("POST", "/indices/salario-minimo", dados),
    remover: (id: string) => requisitar<void>("DELETE", `/indices/salario-minimo/${id}`),
  },
  pagamentos: {
    criar: (parcelaId: string, dados: Partial<PagamentoParcial>) =>
      requisitar<PagamentoParcial>("POST", `/parcelas/${parcelaId}/pagamentos`, dados),
    atualizar: (id: string, dados: Partial<PagamentoParcial>) =>
      requisitar<PagamentoParcial>("PUT", `/pagamentos/${id}`, dados),
    remover: (id: string) => requisitar<void>("DELETE", `/pagamentos/${id}`),
  },
  acessorios: {
    listar: (processoId: string) => requisitar<Acessorio[]>("GET", `/processos/${processoId}/acessorios`),
    criar: (processoId: string, dados: Partial<Acessorio>) =>
      requisitar<Acessorio>("POST", `/processos/${processoId}/acessorios`, dados),
    atualizar: (id: string, dados: Partial<Acessorio>) =>
      requisitar<Acessorio>("PUT", `/acessorios/${id}`, dados),
    remover: (id: string) => requisitar<void>("DELETE", `/acessorios/${id}`),
  },
  deducoes: {
    listar: (processoId: string) => requisitar<Deducao[]>("GET", `/processos/${processoId}/deducoes`),
    criar: (processoId: string, dados: Partial<Deducao>) =>
      requisitar<Deducao>("POST", `/processos/${processoId}/deducoes`, dados),
    atualizar: (id: string, dados: Partial<Deducao>) =>
      requisitar<Deducao>("PUT", `/deducoes/${id}`, dados),
    remover: (id: string) => requisitar<void>("DELETE", `/deducoes/${id}`),
  },
  paradas: {
    listar: (processoId: string) => requisitar<Parada[]>("GET", `/processos/${processoId}/paradas`),
    criar: (processoId: string, dados: Partial<Parada>) =>
      requisitar<Parada>("POST", `/processos/${processoId}/paradas`, dados),
    atualizar: (id: string, dados: Partial<Parada>) =>
      requisitar<Parada>("PUT", `/paradas/${id}`, dados),
    remover: (id: string) => requisitar<void>("DELETE", `/paradas/${id}`),
  },
  backup: {
    exportar: async (): Promise<Blob> => {
      const resposta = await fetch(`${BASE}/backup/exportar`, { method: "POST" });
      if (!resposta.ok) throw new ApiError(resposta.status, resposta.statusText);
      return resposta.blob();
    },
    restaurar: async (arquivo: File): Promise<void> => {
      const formData = new FormData();
      formData.append("arquivo", arquivo);
      const resposta = await fetch(`${BASE}/backup/restaurar`, { method: "POST", body: formData });
      if (!resposta.ok) {
        let detail: unknown;
        try {
          detail = (await resposta.json()).detail;
        } catch {
          detail = resposta.statusText;
        }
        throw new ApiError(resposta.status, detail);
      }
    },
  },
};
