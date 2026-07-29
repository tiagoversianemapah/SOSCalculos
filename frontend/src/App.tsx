import { useState } from "react";
import { Icone } from "./components/ui/Icone";
import { WizardShell } from "./components/wizard/WizardShell";
import { ListaProcessos } from "./routes/ListaProcessos";
import { AcessoriosRoute } from "./routes/acessorios/AcessoriosRoute";
import { CreditosRoute } from "./routes/creditos/CreditosRoute";
import { DeducoesRoute } from "./routes/deducoes/DeducoesRoute";
import { ProcessoRoute } from "./routes/processo/ProcessoRoute";
import { RevisaoRoute } from "./routes/revisao/RevisaoRoute";
import { WizardProvider, useWizard } from "./store/wizardStore";

function WizardConteudo() {
  const { passoAtual, configuraDeducoes } = useWizard();
  switch (passoAtual) {
    case 1:
      return <ProcessoRoute />;
    case 2:
      return <CreditosRoute />;
    case 3:
      return <AcessoriosRoute />;
    case 4:
      return configuraDeducoes ? <DeducoesRoute /> : <RevisaoRoute />;
    case 5:
      return <RevisaoRoute />;
  }
}

function CabecalhoApp() {
  return (
    <header className="app-cabecalho">
      <div className="app-marca">
        <Icone nome="balanca" tamanho={22} />
        Cálculo Judicial
        <span className="app-marca-sub">Liquidação de sentença</span>
      </div>
    </header>
  );
}

function Conteudo({ onSair }: { onSair: () => void }) {
  const { definirProcessoId } = useWizard();
  return (
    <div className="app-corpo">
      <button
        type="button"
        className="voltar-lista discreto"
        onClick={() => {
          definirProcessoId(null);
          onSair();
        }}
      >
        <Icone nome="seta-esquerda" />
        Lista de processos
      </button>
      <WizardShell>
        <WizardConteudo />
      </WizardShell>
    </div>
  );
}

export default function App() {
  const [tela, setTela] = useState<"lista" | "wizard">("lista");
  const [processoInicial, setProcessoInicial] = useState<string | null>(null);

  return (
    <>
      <CabecalhoApp />
      {tela === "lista" ? (
        <ListaProcessos
          onNovo={() => {
            setProcessoInicial(null);
            setTela("wizard");
          }}
          onAbrir={(id) => {
            setProcessoInicial(id);
            setTela("wizard");
          }}
        />
      ) : (
        <WizardProvider key={processoInicial ?? "novo"} processoInicial={processoInicial}>
          <Conteudo onSair={() => setTela("lista")} />
        </WizardProvider>
      )}
    </>
  );
}
