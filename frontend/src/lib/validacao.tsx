// Validação de formulário do wizard — erro no próprio campo, não numa
// faixa no topo da tela.
//
// Regras do comportamento (definidas com o usuário):
//  - o campo que falta fica vermelho;
//  - a mensagem aparece logo abaixo dele;
//  - a tela rola sozinha até o primeiro campo que falta e dá foco nele;
//  - campo que só existe quando uma opção está selecionada não é
//    cobrado enquanto estiver escondido (ver `RegraCampo.valido`);
//  - campo que existe mas está dentro de uma seção recolhida (linha
//    "editar" da planilha, editor "Personalizado…") é cobrado — e a
//    seção é aberta antes de rolar até ele (ver `RegraCampo.revelar`).
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export interface RegraCampo {
  /** Chave única do campo no formulário (ex.: "requerente",
   * "parcela.<id>.valor_bruto", "correcao.0.data_inicio"). */
  nome: string;
  /** `false` reprova o campo. Campo condicional escondido deve passar
   * `true` (ou nem entrar na lista) enquanto não estiver visível. */
  valido: boolean;
  /** Texto exibido abaixo do campo. */
  mensagem: string;
  /** Abre a seção que contém o campo, quando ele está recolhido —
   * chamado antes de rolar/focar. */
  revelar?: () => void;
}

export interface Validacao {
  erros: Record<string, string>;
  registrar: (nome: string) => (el: HTMLElement | null) => void;
  /** Marca os campos reprovados e leva a tela até o primeiro deles.
   * Devolve `true` quando está tudo preenchido. */
  validar: (regras: RegraCampo[]) => boolean;
  limparCampo: (nome: string) => void;
  limparTudo: () => void;
}

const SELETOR_FOCAVEL =
  "input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [contenteditable='true']";

export function useValidacao(): Validacao {
  const [erros, setErros] = useState<Record<string, string>>({});
  const [alvoFoco, setAlvoFoco] = useState<string | null>(null);
  const refs = useRef(new Map<string, HTMLElement>());

  const registrar = useCallback(
    (nome: string) => (el: HTMLElement | null) => {
      if (el) refs.current.set(nome, el);
      else refs.current.delete(nome);
    },
    []
  );

  // Sem lista de dependências de propósito: roda depois de todo commit
  // enquanto houver um alvo pendente. Um campo escondido atrás de uma
  // seção recolhida só entra no DOM no commit SEGUINTE ao que abriu a
  // seção — se desistíssemos na primeira tentativa, a tela não rolaria
  // até ele. Enquanto não achamos o campo, o alvo fica pendente e a
  // próxima renderização tenta de novo (não há setState aqui nesse
  // caminho, então isso não gera laço).
  useEffect(() => {
    if (!alvoFoco) return;
    const container = refs.current.get(alvoFoco);
    if (!container) return;
    setAlvoFoco(null);
    container.scrollIntoView({ behavior: "smooth", block: "center" });
    const focavel = container.matches(SELETOR_FOCAVEL)
      ? container
      : container.querySelector<HTMLElement>(SELETOR_FOCAVEL);
    focavel?.focus({ preventScroll: true });
  });

  const validar = useCallback((regras: RegraCampo[]) => {
    const reprovados = regras.filter((regra) => !regra.valido);
    setErros(Object.fromEntries(reprovados.map((regra) => [regra.nome, regra.mensagem])));
    if (reprovados.length === 0) return true;
    reprovados[0].revelar?.();
    setAlvoFoco(reprovados[0].nome);
    return false;
  }, []);

  const limparCampo = useCallback((nome: string) => {
    setErros((atuais) => {
      if (!(nome in atuais)) return atuais;
      const copia = { ...atuais };
      delete copia[nome];
      return copia;
    });
  }, []);

  const limparTudo = useCallback(() => setErros({}), []);

  return { erros, registrar, validar, limparCampo, limparTudo };
}

/** Validação que não valida nada — para os componentes compartilhados
 * (editores de segmento) quando usados fora de um fluxo validado. */
export const VALIDACAO_INERTE: Validacao = {
  erros: {},
  registrar: () => () => {},
  validar: () => true,
  limparCampo: () => {},
  limparTudo: () => {},
};

interface PropsCampo {
  nome: string;
  validacao: Validacao;
  /** Rótulo do campo — omitido dentro de tabela, onde o cabeçalho já rotula. */
  rotulo?: ReactNode;
  children: ReactNode;
  /** `div` dentro de `<td>`/linha flex; `label` (padrão) em formulário normal. */
  como?: "label" | "div";
  className?: string;
}

/** Envolve um campo para exibir a borda vermelha e a mensagem embaixo.
 * O erro some sozinho assim que o usuário edita qualquer input de
 * dentro (o `onChange` do React borbulha até este wrapper). */
export function Campo({ nome, validacao, rotulo, children, como = "label", className }: PropsCampo) {
  const erro = validacao.erros[nome];
  const classe = ["campo", erro ? "campo-invalido" : "", className ?? ""].filter(Boolean).join(" ");
  const aoEditar = () => {
    if (erro) validacao.limparCampo(nome);
  };
  const conteudo = (
    <>
      {rotulo}
      {children}
      {erro && <span className="campo-erro">{erro}</span>}
    </>
  );
  if (como === "div") {
    return (
      <div ref={validacao.registrar(nome)} className={classe} onChange={aoEditar}>
        {conteudo}
      </div>
    );
  }
  return (
    <label ref={validacao.registrar(nome)} className={classe} onChange={aoEditar}>
      {conteudo}
    </label>
  );
}

/** Regra de campo de texto/data obrigatório. A mensagem usa "Preencha
 * ..." de propósito: "... é obrigatório" erraria o gênero em metade dos
 * rótulos ("a data ... é obrigatório"). */
export function obrigatorio(
  nome: string,
  valor: string | null | undefined,
  rotulo: string,
  revelar?: () => void
): RegraCampo {
  const emMinuscula = rotulo.charAt(0).toLowerCase() + rotulo.slice(1);
  return {
    nome,
    valido: Boolean(valor && valor.trim()),
    mensagem: `Preencha ${emMinuscula}.`,
    revelar,
  };
}
