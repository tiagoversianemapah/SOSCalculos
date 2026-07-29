import type { ReactNode } from "react";
import { useWizard, type Passo } from "../../store/wizardStore";

function passos(configuraDeducoes: boolean): { numero: Passo; titulo: string }[] {
  const base: { numero: Passo; titulo: string }[] = [
    { numero: 1, titulo: "Processo" },
    { numero: 2, titulo: "Créditos" },
    { numero: 3, titulo: "Acessórios" },
  ];
  // "Configurar Deduções" (paridade SOSCálculos, Passo 1) insere um
  // passo extra aqui — Revisão vira o passo 5 nesse caso, e o passo 4
  // continua sendo Revisão quando a opção está desligada.
  if (configuraDeducoes) {
    base.push({ numero: 4, titulo: "Deduções" });
    base.push({ numero: 5, titulo: "Revisão" });
  } else {
    base.push({ numero: 4, titulo: "Revisão" });
  }
  return base;
}

export function WizardShell({ children }: { children: ReactNode }) {
  const { passoAtual, processoId, configuraDeducoes, irParaPasso } = useWizard();

  return (
    <div className="wizard">
      <nav className="wizard-passos">
        {passos(configuraDeducoes).map(({ numero, titulo }) => {
          const alcancavel = numero === 1 || Boolean(processoId);
          return (
            <button
              key={numero}
              type="button"
              className={`wizard-passo ${numero === passoAtual ? "ativo" : ""}`}
              disabled={!alcancavel}
              onClick={() => irParaPasso(numero)}
            >
              <span className="wizard-passo-numero">{numero}</span>
              {titulo}
            </button>
          );
        })}
      </nav>
      <main className="wizard-conteudo">{children}</main>
    </div>
  );
}
