import type { ReactNode } from "react";
import { Icone, type NomeIcone } from "../ui/Icone";
import { useWizard, type Passo } from "../../store/wizardStore";

interface DefinicaoPasso {
  numero: Passo;
  titulo: string;
  icone: NomeIcone;
}

function passos(configuraDeducoes: boolean): DefinicaoPasso[] {
  const base: DefinicaoPasso[] = [
    { numero: 1, titulo: "Processo", icone: "pasta" },
    { numero: 2, titulo: "Créditos", icone: "dinheiro" },
    { numero: 3, titulo: "Acessórios", icone: "percentual" },
  ];
  // "Configurar Deduções" (paridade SOSCálculos, Passo 1) insere um
  // passo extra aqui — Revisão vira o passo 5 nesse caso, e o passo 4
  // continua sendo Revisão quando a opção está desligada.
  if (configuraDeducoes) {
    base.push({ numero: 4, titulo: "Deduções", icone: "menos-circulo" });
    base.push({ numero: 5, titulo: "Revisão", icone: "prancheta" });
  } else {
    base.push({ numero: 4, titulo: "Revisão", icone: "prancheta" });
  }
  return base;
}

export function WizardShell({ children }: { children: ReactNode }) {
  const { passoAtual, processoId, configuraDeducoes, irParaPasso } = useWizard();

  return (
    <div className="wizard">
      <nav className="wizard-passos">
        {passos(configuraDeducoes).map(({ numero, titulo, icone }) => {
          const alcancavel = numero === 1 || Boolean(processoId);
          const ativo = numero === passoAtual;
          // Passo já percorrido ganha o check verde — dá a noção de
          // progresso que a numeração sozinha não dava.
          const concluido = numero < passoAtual && alcancavel;
          return (
            <button
              key={numero}
              type="button"
              className={`wizard-passo ${ativo ? "ativo" : ""} ${concluido ? "concluido" : ""}`}
              disabled={!alcancavel}
              onClick={() => irParaPasso(numero)}
              aria-current={ativo ? "step" : undefined}
            >
              <span className="wizard-passo-numero">
                {concluido ? <Icone nome="check" tamanho={13} /> : numero}
              </span>
              <Icone nome={icone} tamanho={15} />
              <span>{titulo}</span>
            </button>
          );
        })}
      </nav>
      <main className="wizard-conteudo">{children}</main>
    </div>
  );
}
