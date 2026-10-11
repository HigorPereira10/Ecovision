/**
 * app/src/domain/doencas.ts
 *
 * Vocabulário de condições fitossanitárias: traduz o nome técnico que a
 * API devolve ('pinta_preta') para o texto que o produtor lê na tela
 * ('Pinta preta (Alternaria solani)').
 *
 * POR QUE ISSO MORA NO APP, E NÃO NA API: a API devolve dado, a
 * interface decide como escrevê-lo. O backend grava
 * `diagnosticos.classe_prevista` com o nome da classe do modelo (ver
 * cloud/app/core/inference.py), que é estável e serve para consulta e
 * estatística. Rótulo bonito é assunto de tela. Sem esta tradução, a
 * tela de Diagnóstico mostrava literalmente "pinta_preta" ao produtor.
 *
 * ESCOPO ATUAL DO MODELO: a IA em produção reconhece TRÊS condições,
 * listadas em CLASSES_ATIVAS. O modelo nasceu com um recorte pequeno de
 * propósito (ver ml/README.md e ADR 0011): três classes com dados
 * suficientes e validadas por agrônomo valem mais, na banca e na
 * estufa, do que dez classes em que sete chutam. As outras sete ficam
 * aqui com `ativa: false` porque o catálogo agronômico do backend já as
 * cobre e elas voltam a valer quando houver dado para treiná-las. Para
 * reativar uma: trocar `ativa: false` por `ativa: true` AQUI e incluir
 * a classe em _CLASSES_DO_MODELO no backend, na ordem exata da saída do
 * modelo retreinado. As duas pontas têm que concordar, senão cada
 * predição sai com o rótulo de outra doença e nada falha de forma
 * visível.
 *
 * Os nomes científicos aparecem apenas nas classes ativas. Nas
 * inativas ficou só o nome comum de propósito: nenhuma delas chega ao
 * produtor hoje, e escrever um binômio que ninguém conferiu seria
 * criar informação para a banca cobrar depois.
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
}

const CATALOGO: Record<string, CondicaoFitossanitaria> = {
  // --- reconhecidas pelo modelo em produção ---
  saudavel: { rotulo: 'Saudável', ativa: true, saudavel: true },
  septoriose: { rotulo: 'Septoriose (Septoria lycopersici)', ativa: true },
  pinta_preta: { rotulo: 'Pinta preta (Alternaria solani)', ativa: true },

  // --- no catálogo agronômico, aguardando dado de treino ---
  requeima: { rotulo: 'Requeima', ativa: false },
  mancha_bacteriana: { rotulo: 'Mancha bacteriana', ativa: false },
  mofo_de_folha: { rotulo: 'Mofo de folha', ativa: false },
  acaro_rajado: { rotulo: 'Ácaro rajado', ativa: false },
  mancha_alvo: { rotulo: 'Mancha alvo', ativa: false },
  vira_cabeca: { rotulo: 'Vira-cabeça', ativa: false },
  mosaico: { rotulo: 'Mosaico', ativa: false },
};

/** As condições que o modelo em produção realmente reconhece, na ordem
 * em que fazem sentido para leitura (saudável primeiro). Usada no aviso
 * da tela de Diagnóstico, para o produtor saber o que o aparelho sabe
 * ver e, principalmente, o que ele NÃO sabe ver. */
export const CLASSES_ATIVAS: string[] = Object.entries(CATALOGO)
  .filter(([, condicao]) => condicao.ativa)
  .map(([classe]) => classe);

/** Converte 'nome_tecnico' em 'Nome tecnico' para uma classe que não
 * está no catálogo. Acontece se o modelo for retreinado e esta tabela
 * não acompanhar: melhor mostrar um rótulo imperfeito do que uma tela
 * vazia ou um erro. */
function rotuloDeEmergencia(classe: string): string {
  const texto = classe.replace(/_/g, ' ').trim();
  if (texto.length === 0) return 'Classe desconhecida';
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Texto para exibir ao produtor. */
export function rotuloDaClasse(classe: ClasseDiagnostico): string {
  return CATALOGO[classe]?.rotulo ?? rotuloDeEmergencia(classe);
}

/** True quando o diagnóstico é de planta sadia.
 *
 * Decide a cor (verde contra vermelho) e a contagem do card de situação
 * sanitária do Dashboard. Tem fallback por texto porque uma classe nova
 * de planta sadia poderia chegar antes desta tabela ser atualizada, e
 * nesse caso errar para "doente" pintaria de vermelho uma estufa
 * saudável. */
export function ehSaudavel(classe: ClasseDiagnostico): boolean {
  const condicao = CATALOGO[classe];
  if (condicao !== undefined) return condicao.saudavel === true;

  return classe
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .includes('saudavel');
}

/** Frase pronta com o que a IA reconhece hoje, para a tela de
 * Diagnóstico. Deixa explícito o limite do modelo em vez de dar a
 * impressão de que ele identifica qualquer doença de tomate. */
export function resumoDoEscopoDoModelo(): string {
  const rotulos = CLASSES_ATIVAS.map((classe) => rotuloDaClasse(classe).split(' (')[0]);
  return `A análise reconhece ${rotulos.length} condições: ${rotulos.join(', ')}.`;
}
