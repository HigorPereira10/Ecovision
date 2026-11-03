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
  /** true quando NÃO houve diagnóstico. Não é saudável nem doente: é
   * ausência de resposta, e a tela trata em cinza. */
  semDiagnostico?: boolean;
}

/** Classe devolvida pela API quando a foto foi reprovada na guarda de
 * qualidade (cloud/app/core/inference.py), por estar escura demais ou
 * sem detalhe. */
export const CLASSE_IMAGEM_INADEQUADA = 'imagem_inadequada';

/** Classe devolvida quando nenhum modelo está carregado no servidor. */
export const CLASSE_INDISPONIVEL = 'indisponivel';

const CATALOGO: Record<string, CondicaoFitossanitaria> = {
  // --- ausência de diagnóstico, não é resultado ---
  //
  // O modelo tem três saídas e nenhuma delas é "isto não é uma folha":
  // ele distribui qualquer entrada entre as três, e no escuro escolhe
  // "saudável" com confiança altíssima. O servidor passou a recusar
  // classificar foto escura ou sem detalhe, e devolve esta classe no
  // lugar. A foto continua guardada e visível, para o produtor ver com
  // os próprios olhos o que aconteceu.
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

  // Classe do domínio próprio, rotulada nas capturas desta estufa
  // (ADR 0018). Entrou em produção em 2026-11-02.
  //
  // O nome é DESCRITIVO de propósito: afirmar "deficiência de potássio"
  // a partir de uma foto exige saber a adubação, e o sistema não sabe.
  // "Distúrbio fisiológico" é o termo da Embrapa para o quadro, e está
  // no texto da recomendação.
  //
  // Sem esta entrada o app ainda funcionava, porque rotuloDeEmergencia
  // transforma 'estresse_foliar' em 'Estresse foliar'. Mas
  // CLASSES_ATIVAS sai do catálogo, então resumoDoEscopoDoModelo()
  // dizia ao produtor que a análise reconhece 3 condições enquanto a
  // tela mostrava a quarta logo acima.
  estresse_foliar: { rotulo: 'Estresse foliar', ativa: true },

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
  .filter(([, condicao]) => condicao.ativa && condicao.semDiagnostico !== true)
  .map(([classe]) => classe);

/** True quando a API não afirmou diagnóstico nenhum: foto reprovada na
 * guarda de qualidade, ou servidor sem modelo.
 *
 * As telas precisam disso porque o contrário de "saudável" NÃO é
 * "doente" neste sistema: existe um terceiro estado, que é "não dá para
 * dizer". Tratar ausência de resposta como doença encheria o painel de
 * alarme falso; tratar como saudável seria a mentira perigosa que a
 * guarda existe justamente para impedir. */
export function semDiagnostico(classe: ClasseDiagnostico): boolean {
  return CATALOGO[classe]?.semDiagnostico === true;
}

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
  // Atenção: devolver false aqui significa "não é sadia", e não
  // "está doente". Quem precisa da distinção usa semDiagnostico().

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
