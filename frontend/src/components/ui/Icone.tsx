// Ícones em SVG inline — deliberadamente sem biblioteca externa: o app
// roda empacotado e offline (PyInstaller + WebView2), então nada pode
// depender de CDN, fonte de ícone ou requisição em tempo de execução.
// Todos herdam a cor do texto (`currentColor`) e o tamanho vem do
// atributo `tamanho`, então funcionam dentro de botão, título ou tabela
// sem ajuste extra.
import type { ReactNode } from "react";

export type NomeIcone =
  | "balanca"
  | "mais"
  | "fechar"
  | "lixeira"
  | "editar"
  | "seta-esquerda"
  | "seta-direita"
  | "check"
  | "check-circulo"
  | "alerta"
  | "calendario"
  | "baixar"
  | "subir"
  | "documento"
  | "calculadora"
  | "pasta"
  | "dinheiro"
  | "percentual"
  | "menos-circulo"
  | "prancheta"
  | "ajustes"
  | "relogio"
  | "raio"
  | "lista";

const CAMINHOS: Record<NomeIcone, ReactNode> = {
  balanca: (
    <>
      <path d="M12 3v18" />
      <path d="M8 21h8" />
      <path d="M3 7h18" />
      <path d="M6.5 7 3 14h7L6.5 7Z" />
      <path d="M17.5 7 14 14h7l-3.5-7Z" />
    </>
  ),
  mais: (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  fechar: (
    <>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </>
  ),
  lixeira: (
    <>
      <path d="M3 6h18" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </>
  ),
  editar: (
    <>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z" />
    </>
  ),
  "seta-esquerda": (
    <>
      <path d="M19 12H5" />
      <path d="m12 19-7-7 7-7" />
    </>
  ),
  "seta-direita": (
    <>
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </>
  ),
  check: <path d="M20 6 9 17l-5-5" />,
  "check-circulo": (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  alerta: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </>
  ),
  calendario: (
    <>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4" />
      <path d="M8 2v4" />
      <path d="M3 10h18" />
    </>
  ),
  baixar: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="m7 10 5 5 5-5" />
      <path d="M12 15V3" />
    </>
  ),
  subir: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="m17 8-5-5-5 5" />
      <path d="M12 3v12" />
    </>
  ),
  documento: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
      <path d="M16 13H8" />
      <path d="M16 17H8" />
      <path d="M10 9H8" />
    </>
  ),
  calculadora: (
    <>
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <path d="M8 6h8" />
      <path d="M8 11h.01" />
      <path d="M12 11h.01" />
      <path d="M16 11h.01" />
      <path d="M8 15h.01" />
      <path d="M12 15h.01" />
      <path d="M16 15v4" />
      <path d="M8 19h4" />
    </>
  ),
  pasta: (
    <>
      <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    </>
  ),
  dinheiro: (
    <>
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M6 12h.01" />
      <path d="M18 12h.01" />
    </>
  ),
  percentual: (
    <>
      <path d="M19 5 5 19" />
      <circle cx="6.5" cy="6.5" r="2.5" />
      <circle cx="17.5" cy="17.5" r="2.5" />
    </>
  ),
  "menos-circulo": (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M8 12h8" />
    </>
  ),
  prancheta: (
    <>
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="m9 14 2 2 4-4" />
    </>
  ),
  ajustes: (
    <>
      <path d="M4 21v-7" />
      <path d="M4 10V3" />
      <path d="M12 21v-9" />
      <path d="M12 8V3" />
      <path d="M20 21v-5" />
      <path d="M20 12V3" />
      <path d="M1 14h6" />
      <path d="M9 8h6" />
      <path d="M17 16h6" />
    </>
  ),
  relogio: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </>
  ),
  raio: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z" />,
  lista: (
    <>
      <path d="M8 6h13" />
      <path d="M8 12h13" />
      <path d="M8 18h13" />
      <path d="M3 6h.01" />
      <path d="M3 12h.01" />
      <path d="M3 18h.01" />
    </>
  ),
};

interface Props {
  nome: NomeIcone;
  tamanho?: number;
  className?: string;
  /** Ícone puramente decorativo fica escondido de leitor de tela (padrão).
   * Passe um rótulo quando o ícone for a única informação do controle. */
  rotulo?: string;
}

export function Icone({ nome, tamanho = 16, className, rotulo }: Props) {
  return (
    <svg
      className={["icone", className].filter(Boolean).join(" ")}
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={rotulo ? undefined : true}
      role={rotulo ? "img" : undefined}
      focusable="false"
    >
      {rotulo && <title>{rotulo}</title>}
      {CAMINHOS[nome]}
    </svg>
  );
}
