// Estado do wizard entre os passos (seção 6.2): qual processo está
// sendo editado e em que passo o usuário está. Cada rota busca seus
// próprios dados (parcelas, acessórios...) via api.ts — este store não
// duplica cache, só guarda o "onde estou".
//
// `configuraDeducoes` (paridade SOSCálculos) espelha
// `Processo.configura_deducoes` — quando true, o wizard ganha um passo
// extra ("Deduções", passo 4) e Revisão vira o passo 5; quando false,
// Revisão continua sendo o passo 4, como sempre foi. Buscado aqui (não
// em cada rota) pra WizardShell e App.tsx concordarem sobre quantos
// passos existem sem duplicar a chamada à API.
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "../lib/api";

export type Passo = 1 | 2 | 3 | 4 | 5;

interface WizardState {
  processoId: string | null;
  passoAtual: Passo;
  configuraDeducoes: boolean;
  definirProcessoId: (id: string | null) => void;
  definirConfiguraDeducoes: (valor: boolean) => void;
  irParaPasso: (passo: Passo) => void;
}

const WizardContext = createContext<WizardState | null>(null);

export function WizardProvider({
  children,
  processoInicial = null,
}: {
  children: ReactNode;
  processoInicial?: string | null;
}) {
  const [processoId, setProcessoId] = useState<string | null>(processoInicial);
  // Ref espelhando processoId: `definirProcessoId` seguido de
  // `irParaPasso` no mesmo handler (ex.: salvar processo → avançar)
  // rodaria com o `processoId` ainda desatualizado (closure do state
  // antigo, já que o setState é assíncrono) — a ref é atualizada na
  // hora, então a guarda abaixo sempre vê o valor certo.
  const processoIdRef = useRef(processoInicial);
  const [passoAtual, setPassoAtual] = useState<Passo>(1);
  const [configuraDeducoes, setConfiguraDeducoes] = useState(false);

  useEffect(() => {
    if (!processoId) {
      setConfiguraDeducoes(false);
      return;
    }
    api.processos.obter(processoId).then((p) => setConfiguraDeducoes(p.configura_deducoes));
  }, [processoId]);

  const definirProcessoId = (id: string | null) => {
    processoIdRef.current = id;
    setProcessoId(id);
  };
  const irParaPasso = (passo: Passo) => {
    // guarda: não avança além do passo 1 sem processo salvo (precisa de
    // processo_id pra anexar parcelas/acessórios/paradas).
    if (passo > 1 && !processoIdRef.current) return;
    setPassoAtual(passo);
  };

  return (
    <WizardContext.Provider
      value={{
        processoId,
        passoAtual,
        configuraDeducoes,
        definirProcessoId,
        definirConfiguraDeducoes: setConfiguraDeducoes,
        irParaPasso,
      }}
    >
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard(): WizardState {
  const contexto = useContext(WizardContext);
  if (!contexto) throw new Error("useWizard precisa estar dentro de um WizardProvider");
  return contexto;
}
