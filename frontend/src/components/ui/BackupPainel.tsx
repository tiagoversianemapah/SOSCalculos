// Backup/restauração do dados.db (seção 9) — única proteção contra
// perda de disco; fica visível na tela inicial, não escondido em menu.
import { useRef, useState } from "react";
import { api } from "../../lib/api";

export function BackupPainel({ onRestaurado }: { onRestaurado: () => void }) {
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [processando, setProcessando] = useState(false);
  const inputArquivo = useRef<HTMLInputElement>(null);

  const exportar = async () => {
    setProcessando(true);
    setErro(null);
    setMensagem(null);
    try {
      const blob = await api.backup.exportar();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `calculo-judicial-backup-${new Date().toISOString().slice(0, 10)}.db`;
      // precisa estar no DOM pro clique disparar o download de forma
      // confiável em todo navegador/webview — clicar num <a> solto
      // funciona na maioria dos casos, mas não é garantido.
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setMensagem("Backup exportado.");
    } catch {
      setErro("Falha ao exportar o backup.");
    } finally {
      setProcessando(false);
    }
  };

  const restaurarArquivoEscolhido = async (arquivo: File) => {
    setProcessando(true);
    setErro(null);
    setMensagem(null);
    try {
      await api.backup.restaurar(arquivo);
      setMensagem("Backup restaurado — a lista de processos foi atualizada.");
      onRestaurado();
    } catch {
      setErro("Falha ao restaurar: o arquivo não parece ser um backup válido.");
    } finally {
      setProcessando(false);
    }
  };

  return (
    <div className="backup-painel">
      <button type="button" onClick={exportar} disabled={processando}>
        Exportar backup
      </button>
      <button type="button" onClick={() => inputArquivo.current?.click()} disabled={processando}>
        Restaurar backup
      </button>
      <input
        ref={inputArquivo}
        type="file"
        accept=".db"
        style={{ display: "none" }}
        onChange={(e) => {
          const arquivo = e.target.files?.[0];
          if (arquivo) restaurarArquivoEscolhido(arquivo);
          e.target.value = "";
        }}
      />
      {mensagem && <span className="texto-auxiliar">{mensagem}</span>}
      {erro && <span className="erro">{erro}</span>}
    </div>
  );
}
