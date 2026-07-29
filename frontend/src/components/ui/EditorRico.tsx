// Editor de texto rico minimalista (contentEditable + execCommand) pro
// campo "Observações" do passo 1 — paridade visual com a barra de
// formatação do SOSCálculos (negrito, itálico, sublinhado, tachado,
// alinhamento, listas). Guarda HTML puro em `valor`; sem dependências
// externas (o app roda 100% offline/empacotado, seção 6.1).
import { useEffect, useRef } from "react";

interface Props {
  valor: string;
  onChange: (html: string) => void;
}

const BOTOES: { comando: string; rotulo: string; argumento?: string }[] = [
  { comando: "bold", rotulo: "B" },
  { comando: "italic", rotulo: "I" },
  { comando: "underline", rotulo: "U" },
  { comando: "strikeThrough", rotulo: "S" },
  { comando: "justifyLeft", rotulo: "⇤" },
  { comando: "justifyCenter", rotulo: "≡" },
  { comando: "justifyRight", rotulo: "⇥" },
  { comando: "insertUnorderedList", rotulo: "•" },
  { comando: "insertOrderedList", rotulo: "1." },
];

export function EditorRico({ valor, onChange }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // Só sincroniza do estado externo quando o conteúdo mudou por fora
  // (ex.: carregar um processo existente) — nunca a cada tecla, senão o
  // cursor pula pro início a cada digitação.
  useEffect(() => {
    if (ref.current && ref.current.innerHTML !== (valor || "")) {
      ref.current.innerHTML = valor || "";
    }
  }, [valor]);

  const executar = (comando: string) => {
    ref.current?.focus();
    document.execCommand(comando, false);
    onChange(ref.current?.innerHTML ?? "");
  };

  return (
    <div className="editor-rico">
      <div className="editor-rico-barra">
        {BOTOES.map((botao) => (
          <button
            key={botao.comando}
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => executar(botao.comando)}
          >
            {botao.rotulo}
          </button>
        ))}
      </div>
      <div
        ref={ref}
        className="editor-rico-area"
        contentEditable
        onInput={(e) => onChange((e.target as HTMLDivElement).innerHTML)}
      />
    </div>
  );
}
