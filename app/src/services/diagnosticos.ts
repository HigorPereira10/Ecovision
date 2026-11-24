/**
 * Diagnósticos da IA, a partir de GET /diagnosticos.
 *
 * Cada item já traz a URL assinada da imagem, de validade curta, que pode
 * vir nula se a geração falhar; nesse caso a tela mostra um marcador.
 * Os nomes da API (classe_prevista, criado_em, device_id) são convertidos
 * para os usados pelas telas (classificacao, timestamp, dispositivo_id);
 * `classificacao` já vem traduzida por src/domain/doencas.ts, e `classe`
 * mantém o nome técnico.
 */

import { get } from './api';
import {
  ehDoenca,
  ehEstresse,
  ehSaudavel,
  rotuloDaClasse,
  semDiagnostico,
} from '../domain/doencas';

/** Janela padrão: 7 dias, a mesma de services/leituras.ts. O Histórico
 * pede sem janela (null), porque o filtro "Todo o período" só pode filtrar
 * o que foi baixado; sem janela a API devolve até 1000 itens. */
const JANELA_PADRAO_HORAS = 168;

/** Quantidade de itens pedida pela tela de Diagnóstico: cada item exige uma
 * URL assinada, e a tela mostra o diagnóstico atual e algumas miniaturas. */
const ITENS_TELA_DIAGNOSTICO = 12;

/** Formato devolvido pela API (GET /diagnosticos). */
interface DiagnosticoDaApi {
  id: number;
  device_id: string;
  classe_prevista: string;
  confianca: number;
  recomendacao: string | null;
  caminho_arquivo: string;
  url_imagem: string | null;
  criado_em: string;
}

export interface Diagnostico {
  id: number;
  dispositivo_id: string;
  /** Nome técnico da classe ('pinta_preta'), para comparação. */
  classe: string;
  /** Rótulo pronto para exibir ('Pinta preta (Alternaria solani)'). */
  classificacao: string;
  confianca: number;
  recomendacao: string | null;
  /** Signed URL pronta para exibir, ou null se não houver imagem. */
  urlImagem: string | null;
  saudavel: boolean;
  /** true quando a API não afirmou diagnóstico (foto reprovada na
   * verificação de qualidade ou servidor sem modelo); `recomendacao` traz
   * o motivo e a tela não diz nada sobre a planta. */
  semDiagnostico: boolean;
  /** Alteração visível na folha sem doença identificada. Não é saudável
   * nem doença: é o terceiro estado, e as telas pintam de âmbar. */
  estresse: boolean;
  /** Doença identificada pelo modelo (septoriose, pinta preta). */
  doenca: boolean;
  timestamp: string;
}

function traduzir(bruto: DiagnosticoDaApi): Diagnostico {
  return {
    id: bruto.id,
    dispositivo_id: bruto.device_id,
    classe: bruto.classe_prevista,
    classificacao: rotuloDaClasse(bruto.classe_prevista),
    confianca: bruto.confianca,
    recomendacao: bruto.recomendacao,
    urlImagem: bruto.url_imagem,
    saudavel: ehSaudavel(bruto.classe_prevista),
    semDiagnostico: semDiagnostico(bruto.classe_prevista),
    estresse: ehEstresse(bruto.classe_prevista),
    doenca: ehDoenca(bruto.classe_prevista),
    timestamp: bruto.criado_em,
  };
}

/**
 * Diagnósticos da janela informada, do mais recente ao mais antigo; com
 * `horas` null, sem corte de período. A ordenação é garantida aqui, pois as
 * telas tratam o item [0] como o diagnóstico atual.
 */
export async function getDiagnosticos(
  horas: number | null = JANELA_PADRAO_HORAS,
  limite?: number,
): Promise<Diagnostico[]> {
  const parametros = new URLSearchParams();
  if (horas !== null) parametros.set('horas', String(horas));
  if (limite !== undefined) parametros.set('limite', String(limite));

  const consulta = parametros.toString();
  const brutos = await get<DiagnosticoDaApi[]>(`/diagnosticos${consulta ? `?${consulta}` : ''}`);
  return brutos
    .map(traduzir)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

/** Os diagnósticos mais recentes, para a tela de Diagnóstico e para o
 * card de situação sanitária do Início. Pede poucos itens de propósito,
 * ver ITENS_TELA_DIAGNOSTICO. */
export async function getDiagnosticosRecentes(): Promise<Diagnostico[]> {
  return getDiagnosticos(JANELA_PADRAO_HORAS, ITENS_TELA_DIAGNOSTICO);
}
