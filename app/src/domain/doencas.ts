/**
 * Vocabulário de condições fitossanitárias: traduz o nome técnico devolvido
 * pela API ('pinta_preta') para o texto exibido ('Pinta preta (Alternaria
 * solani)').
 *
 * As classes com `ativa: true` são as reconhecidas pelo modelo em produção;
 * as demais acompanham o catálogo agronômico do servidor e podem ser
 * reativadas se o modelo for treinado com elas. Para reativar uma classe,
 * marque `ativa: true` aqui e inclua-a em _CLASSES_DO_MODELO no servidor,
 * na ordem exata das saídas do modelo; as duas pontas precisam coincidir.
 * Os nomes científicos aparecem apenas nas classes ativas.
 */

/** Nome técnico da classe, exatamente como a API devolve. */
export type ClasseDiagnostico = string;

interface CondicaoFitossanitaria {
  /** Texto exibido ao produtor. */
  rotulo: string;
  /** false = o modelo atual não emite esta classe (ver cabeçalho). */
  ativa: boolean;
  /** true apenas para a ausência de doença, que a tela pinta de verde. */
  saudavel?: boolean;
  /** true quando não houve diagnóstico: ausência de resposta, exibida em
   * cinza. */
  semDiagnostico?: boolean;
  /** true para alteração visível na folha que não é doença conhecida,
   * exibida em âmbar (pede atenção, não tratamento). */
  estresse?: boolean;
}

/** Classe devolvida pela API quando a foto foi reprovada na verificação de
 * qualidade, por estar escura demais ou sem detalhe. */
export const CLASSE_IMAGEM_INADEQUADA = 'imagem_inadequada';

/** Classe devolvida quando nenhum modelo está carregado no servidor. */
export const CLASSE_INDISPONIVEL = 'indisponivel';

const CATALOGO: Record<string, CondicaoFitossanitaria> = {
  // --- ausência de diagnóstico ---
  // O servidor não classifica fotos escuras ou sem detalhe; a foto
  // continua disponível para o produtor conferir.
  [CLASSE_IMAGEM_INADEQUADA]: {
    rotulo: 'Sem análise',
    ativa: true,
    semDiagnostico: true,
  },
  [CLASSE_INDISPONIVEL]: {
    rotulo: 'Análise indisponível',
    ativa: true,
    semDiagnostico: true,
  },

  // --- reconhecidas pelo modelo em produção ---
  saudavel: { rotulo: 'Saudável', ativa: true, saudavel: true },
  septoriose: { rotulo: 'Septoriose (Septoria lycopersici)', ativa: true },
  pinta_preta: { rotulo: 'Pinta preta (Alternaria solani)', ativa: true },

  // Classe rotulada nas capturas do próprio dispositivo. O nome é
  // descritivo: não afirma a causa da alteração. "Distúrbio fisiológico",
  // termo da Embrapa para o quadro, aparece no texto da recomendação.
  estresse_foliar: { rotulo: 'Estresse foliar', ativa: true, estresse: true },

  // --- no catálogo agronômico, aguardando dado de treino ---
  requeima: { rotulo: 'Requeima', ativa: false },
  mancha_bacteriana: { rotulo: 'Mancha bacteriana', ativa: false },
  mofo_de_folha: { rotulo: 'Mofo de folha', ativa: false },
  acaro_rajado: { rotulo: 'Ácaro rajado', ativa: false },
  mancha_alvo: { rotulo: 'Mancha alvo', ativa: false },
  vira_cabeca: { rotulo: 'Vira-cabeça', ativa: false },
  mosaico: { rotulo: 'Mosaico', ativa: false },
};

/** Condições reconhecidas pelo modelo em produção, em ordem de leitura
 * (saudável primeiro), exibidas no aviso de escopo da tela de Diagnóstico. */
export const CLASSES_ATIVAS: string[] = Object.entries(CATALOGO)
  .filter(([, condicao]) => condicao.ativa && condicao.semDiagnostico !== true)
  .map(([classe]) => classe);

/** True quando a API não afirmou diagnóstico: foto reprovada na
 * verificação de qualidade ou servidor sem modelo. Esse estado não conta
 * como saudável nem como doença. */
export function semDiagnostico(classe: ClasseDiagnostico): boolean {
  return CATALOGO[classe]?.semDiagnostico === true;
}

/** Converte 'nome_tecnico' em 'Nome tecnico' para uma classe fora do
 * catálogo, em vez de exibir tela vazia ou erro. */
function rotuloDeEmergencia(classe: string): string {
  const texto = classe.replace(/_/g, ' ').trim();
  if (texto.length === 0) return 'Classe desconhecida';
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Texto para exibir ao produtor. */
export function rotuloDaClasse(classe: ClasseDiagnostico): string {
  return CATALOGO[classe]?.rotulo ?? rotuloDeEmergencia(classe);
}

/** True quando o diagnóstico é de planta sadia. Tem recurso por texto para
 * que uma classe nova de planta sadia não seja contada como doença. */
export function ehSaudavel(classe: ClasseDiagnostico): boolean {
  const condicao = CATALOGO[classe];
  if (condicao !== undefined) return condicao.saudavel === true;
  // Atenção: devolver false aqui significa "não é sadia", e não
  // "está doente". Quem precisa da distinção usa semDiagnostico().

  return classe
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .includes('saudavel');
}

/** True quando há alteração na folha sem doença identificada. Tem recurso
 * por texto para que uma classe nova de estresse não seja contada como
 * doença. */
export function ehEstresse(classe: ClasseDiagnostico): boolean {
  const condicao = CATALOGO[classe];
  if (condicao !== undefined) return condicao.estresse === true;

  return classe.toLowerCase().includes('estresse');
}

/** True quando o diagnóstico é de doença identificada, definida por
 * exclusão: na dúvida, o sistema avisa em vez de calar. */
export function ehDoenca(classe: ClasseDiagnostico): boolean {
  return !ehSaudavel(classe) && !ehEstresse(classe) && !semDiagnostico(classe);
}

/** Frase com as condições que a IA reconhece, para a tela de Diagnóstico
 * deixar claro o limite do modelo. */
export function resumoDoEscopoDoModelo(): string {
  const rotulos = CLASSES_ATIVAS.map((classe) => rotuloDaClasse(classe).split(' (')[0]);
  return `A análise reconhece ${rotulos.length} condições: ${rotulos.join(', ')}.`;
}
