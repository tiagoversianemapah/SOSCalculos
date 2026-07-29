// Espelha app/schemas/*.py e app/engine/types.py (seção 2/4.5) — valores
// monetários/percentuais chegam e saem como string (nunca number solto).

export type Indice =
  | "ipca"
  | "ipca_e"
  | "inpc"
  | "igp_m"
  | "igp_di"
  | "selic_simples"
  | "selic_composta"
  | "tr"
  | "tbf"
  | "tlp"
  | "poupanca"
  | "ptax"
  | "salario_minimo"
  | "tribunal"
  | "pis_pasep"
  | "sem_correcao";

export const INDICES: { value: Indice; label: string }[] = [
  { value: "ipca", label: "IPCA" },
  { value: "ipca_e", label: "IPCA-E" },
  { value: "inpc", label: "INPC" },
  { value: "igp_m", label: "IGP-M" },
  { value: "igp_di", label: "IGP-DI" },
  { value: "selic_simples", label: "Selic Simples" },
  { value: "selic_composta", label: "Selic Composta" },
  { value: "tr", label: "TR" },
  { value: "tbf", label: "TBF" },
  { value: "tlp", label: "TLP" },
  { value: "poupanca", label: "Poupança" },
  { value: "ptax", label: "PTAX" },
  { value: "salario_minimo", label: "Salário Mínimo" },
  { value: "tribunal", label: "Tabela de tribunal" },
  { value: "pis_pasep", label: "Pis/Pasep" },
  { value: "sem_correcao", label: "Sem correção" },
];

export type TipoTaxaJuros = "percentual_fixo_mensal" | "taxa_legal" | "selic_substitutiva";

export const TIPOS_TAXA_JUROS: { value: TipoTaxaJuros; label: string }[] = [
  { value: "percentual_fixo_mensal", label: "Percentual fixo mensal" },
  { value: "taxa_legal", label: "Taxa legal (Selic do mês)" },
  { value: "selic_substitutiva", label: "Selic substitutiva (correção + juros)" },
];

export type BaseCalculoAcessorio =
  | "total_liquido_parcelas"
  | "valor_principal_sem_correcao"
  | "valor_fixo_absoluto"
  | "saldo_remanescente_em_data_evento"
  | "valor_da_causa";

export type TipoAcessorio =
  | "honorarios_sucumbencia"
  | "multa_523_cpc"
  | "honorarios_523_cpc"
  | "honorarios_contratuais"
  | "honorarios_execucao"
  | "multa"
  | "custas_processuais";

export const TIPOS_ACESSORIO: { value: TipoAcessorio; label: string }[] = [
  { value: "honorarios_sucumbencia", label: "Honorários de sucumbência" },
  { value: "multa_523_cpc", label: "Multa do art. 523 CPC" },
  { value: "honorarios_523_cpc", label: "Honorários do art. 523 CPC" },
  { value: "honorarios_contratuais", label: "Honorários contratuais" },
  { value: "honorarios_execucao", label: "Honorários de execução" },
  { value: "multa", label: "Multa" },
  { value: "custas_processuais", label: "Custas processuais" },
];

export type TipoPagamentoParcial = "pagamento" | "deposito_judicial" | "compensacao" | "outro";

export const TIPOS_PAGAMENTO: { value: TipoPagamentoParcial; label: string }[] = [
  { value: "pagamento", label: "Pagamento" },
  { value: "deposito_judicial", label: "Depósito judicial" },
  { value: "compensacao", label: "Compensação" },
  { value: "outro", label: "Outro" },
];

// Campo "Tipo" do passo "Deduções" (paridade SOSCálculos, só existe
// quando Processo.configura_deducoes é true).
export type TipoDeducao =
  | "adjudicacao"
  | "alvara_levantamento"
  | "alvara_levantamento_estimar_tema_677"
  | "compensacao"
  | "compensacao_financeiro"
  | "deposito_judicial"
  | "deposito_judicial_tema_677"
  | "pagamento"
  | "recibo";

export const TIPOS_DEDUCAO: { value: TipoDeducao; label: string }[] = [
  { value: "adjudicacao", label: "Adjudicação" },
  { value: "alvara_levantamento", label: "Alvará de levantamento" },
  { value: "alvara_levantamento_estimar_tema_677", label: "Alvará de levantamento (estimar) - Tema 677" },
  { value: "compensacao", label: "Compensação" },
  { value: "compensacao_financeiro", label: "Compensação Financeiro" },
  { value: "deposito_judicial", label: "Depósito Judicial" },
  { value: "deposito_judicial_tema_677", label: "Depósito Judicial - Tema 677" },
  { value: "pagamento", label: "Pagamento" },
  { value: "recibo", label: "Recibo" },
];

// Campo "Atualização" da dedução — de qual data a correção/juros
// próprios da linha passam a contar.
export type TipoAtualizacaoDeducao = "data_inicial" | "data_calculo" | "data_levantamento" | "outra_data";

export const TIPOS_ATUALIZACAO_DEDUCAO: { value: TipoAtualizacaoDeducao; label: string }[] = [
  { value: "data_inicial", label: "Data inicial" },
  { value: "data_calculo", label: "Data do cálculo" },
  { value: "data_levantamento", label: "Data do levantamento" },
  { value: "outra_data", label: "Outra Data" },
];

// Campo "Vencimento da C.M." / "Tipo Vencimento Juros" do passo 1
// (paridade SOSCálculos) — só decide qual data-âncora do processo
// pré-preenche o data_inicio do segmento no formulário.
export type TipoVencimento =
  | "do_vencimento"
  | "da_citacao"
  | "da_distribuicao"
  | "da_sentenca"
  | "do_evento"
  | "do_transito_julgado"
  | "da_publicacao"
  | "da_data_fixa"
  | "da_homologacao"
  | "da_aposentadoria";

export const TIPOS_VENCIMENTO: { value: TipoVencimento; label: string }[] = [
  { value: "do_vencimento", label: "Do Vencimento" },
  { value: "da_citacao", label: "Da Citação" },
  { value: "da_distribuicao", label: "Da Distribuição" },
  { value: "da_sentenca", label: "Da Sentença" },
  { value: "do_evento", label: "Do Evento" },
  { value: "do_transito_julgado", label: "Do Trânsito em Julgado" },
  { value: "da_publicacao", label: "Da Publicação" },
  { value: "da_data_fixa", label: "Da Data Fixa" },
  { value: "da_homologacao", label: "Da Homologação" },
  { value: "da_aposentadoria", label: "Da Aposentadoria" },
];

// Mapeia cada TipoVencimento (exceto "do_vencimento", que usa o
// vencimento da própria parcela) para o campo de data-âncora
// correspondente em Processo.
export const CAMPO_DATA_ANCORA: Partial<Record<TipoVencimento, keyof Processo>> = {
  da_citacao: "data_citacao",
  da_distribuicao: "data_distribuicao",
  da_sentenca: "data_sentenca",
  do_evento: "data_evento_padrao",
  do_transito_julgado: "data_transito_julgado",
  da_publicacao: "data_publicacao",
  da_data_fixa: "data_fixa",
  da_homologacao: "data_homologacao",
  da_aposentadoria: "data_aposentadoria",
};

export type ContagemJuros = "pro_rata" | "por_competencia";

export const CONTAGENS_JUROS: { value: ContagemJuros; label: string }[] = [
  { value: "pro_rata", label: "Pró-rata" },
  { value: "por_competencia", label: "Por Competência" },
];

export interface CorrecaoSegmento {
  id?: string;
  ordem: number;
  indice: Indice;
  tribunal_codigo?: string | null;
  data_inicio: string;
  data_fim?: string | null;
  fonte_criterio?: string | null;
  vencimento_tipo: TipoVencimento;
  permite_deflacao: boolean;
  compor_com_selic: boolean;
}

export interface JurosSegmento {
  id?: string;
  ordem: number;
  tipo_taxa: TipoTaxaJuros;
  taxa_valor?: string | null;
  data_inicio: string;
  data_fim?: string | null;
  fonte_criterio?: string | null;
  vencimento_tipo: TipoVencimento;
}

export interface PagamentoParcial {
  id: string;
  data: string;
  valor: string;
  tipo: TipoPagamentoParcial;
  descricao?: string | null;
  fonte_criterio?: string | null;
}

export interface Parcela {
  id: string;
  processo_id: string;
  vencimento: string;
  historico: string;
  valor_bruto: string;
  valor_apurado: string | null;
  usa_correcao_default: boolean;
  usa_juros_default: boolean;
  multa_percentual?: string | null;
  pagamentos: PagamentoParcial[];
  correcao_segmentos_override: CorrecaoSegmento[];
  juros_segmentos_override: JurosSegmento[];
}

export interface Deducao {
  id: string;
  tipo: TipoDeducao;
  historico?: string | null;
  data_inicial: string;
  valor: string;
  atualizacao_tipo: TipoAtualizacaoDeducao;
  data_atualizacao?: string | null;
  fonte_criterio?: string | null;
  usa_correcao_default: boolean;
  usa_juros_default: boolean;
  correcao_segmentos_override: CorrecaoSegmento[];
  juros_segmentos_override: JurosSegmento[];
}

export interface Acessorio {
  id: string;
  tipo: TipoAcessorio;
  historico?: string | null;
  percentual?: string | null;
  valor_fixo?: string | null;
  base_calculo: BaseCalculoAcessorio;
  data_evento?: string | null;
  fonte_criterio?: string | null;
  // Multa "Diária (Data final)" — quando preenchido, substitui
  // valor_fixo (total = valor_diario × dias entre data_inicio_acumulo
  // e data_evento, que funciona como a "Data Fim" nesse modo).
  valor_diario?: string | null;
  data_inicio_acumulo?: string | null;
  // Multa "Diária (Competência)" — mesmos campos acima, mas quebra por
  // mês civil (soma de sub-timelines por competência).
  diaria_por_competencia?: boolean;
  // Multa "Salário Mínimo" — quantidade × valor vigente em data_evento
  // (aqui rotulado "Data Salário Mínimo"); substitui valor_fixo.
  salario_minimo_quantidade?: string | null;
  // Multa "Mensal" — um lançamento de valor_mensal por mês vencido
  // entre data_inicio_acumulo e data_evento.
  valor_mensal?: string | null;
  // Só fazem sentido quando base_calculo = "valor_fixo_absoluto" —
  // "Tabela de C.M." / "Juros de Mora" do modo "Valor Monetário"
  // (passo 3, paridade SOSCálculos).
  usa_correcao_default: boolean;
  usa_juros_default: boolean;
  correcao_segmentos_override: CorrecaoSegmento[];
  juros_segmentos_override: JurosSegmento[];
}

export interface Parada {
  id: string;
  data_inicio: string;
  data_fim: string;
  motivo: string;
  suspende_correcao: boolean;
  suspende_juros: boolean;
}

export interface Processo {
  id: string;
  requerente: string;
  requerido: string;
  data_calculo: string;
  numero_processo?: string | null;
  comarca?: string | null;
  vara?: string | null;
  contrato?: string | null;
  feito?: string | null;
  titulo_calculo?: string | null;
  requerente_doc?: string | null;
  requerido_doc?: string | null;
  tribunal?: string | null;
  tipo_acao?: string | null;
  observacoes?: string | null;
  exibir_relatorio_detalhado: boolean;
  exibir_relatorio_correcao: boolean;
  contagem_juros: ContagemJuros;
  // "Configurar Deduções" (Sim habilita o passo extra "Deduções") e
  // "Aplicar Art. 354 do CC" (paridade SOSCálculos) — ver
  // especificacao-tecnica-motor-calculo-judicial.md seção 11.
  configura_deducoes: boolean;
  aplicar_art_354_cc: boolean;
  data_citacao?: string | null;
  data_distribuicao?: string | null;
  data_sentenca?: string | null;
  data_transito_julgado?: string | null;
  data_publicacao?: string | null;
  data_fixa?: string | null;
  data_homologacao?: string | null;
  data_aposentadoria?: string | null;
  data_evento_padrao?: string | null;
  valor_causa?: string | null;
  correcao_segmentos_default: CorrecaoSegmento[];
  juros_segmentos_default: JurosSegmento[];
}

export interface ProcessoListItem {
  id: string;
  numero_processo?: string | null;
  requerente: string;
  requerido: string;
  data_calculo: string;
  ultimo_total_apurado: string | null;
}

export interface LinhaMemoria {
  competencia: string;
  saldo_inicio: string;
  indice: Indice | null;
  variacao_indice: string;
  saldo_corrigido: string;
  tipo_taxa_juros: TipoTaxaJuros | null;
  taxa_juros_mensal: string;
  juros_mes: string;
  saldo_final: string;
  parada_ativa: boolean;
  quitado: boolean;
}

export interface ResultadoParcela {
  parcela_id: string;
  valor_apurado: string;
  memoria: LinhaMemoria[];
}

export interface ResultadoAcessorio {
  acessorio_id: string;
  valor_apurado: string;
  memoria: LinhaMemoria[];
}

export interface ResultadoDeducao {
  deducao_id: string;
  valor_apurado: string;
  memoria: LinhaMemoria[];
}

export interface CalculoPreview {
  parcelas: ResultadoParcela[];
  acessorios: ResultadoAcessorio[];
  deducoes: ResultadoDeducao[];
  total_geral: string;
}

// Cadastro manual do valor absoluto (R$) do salário mínimo — botão
// "Salário Mínimo" do passo 2. Ver app/models/salario_minimo_valor.py:
// deliberadamente não automatizado nem hardcoded, o usuário cadastra os
// valores oficiais de cada decreto.
export interface SalarioMinimoValor {
  id: string;
  competencia: string;
  valor: string;
}

export interface GerarPorSalarioMinimoRequest {
  data_inicial: string;
  data_final: string;
  percentual_salario: string;
  percentual_pago?: string | null;
  fim_mes: boolean;
  historico: string;
  usa_correcao_default: boolean;
  usa_juros_default: boolean;
  multa_percentual?: string | null;
}
