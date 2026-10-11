/**
 * app/src/services/diagnosticos.ts
 *
 * Camada de dados para os diagnósticos da IA. Consome GET /diagnosticos
 * da API real (ver cloud/app/api/routes/historico.py).
 *
 * Até 2026-10-11 este módulo lia de src/mocks/diagnosticos.json e
 * src/mocks/imagens.json. Os dois mocks foram apagados junto com esta
 * troca: enquanto existiam, o Dashboard e a tela de Diagnóstico
 * mostravam temperatura real de um lado e folha inventada do outro, o
 * que é pior do que mostrar uma tela vazia.
 *
 * DUAS CHAMADAS VIRARAM UMA: antes a tela buscava o diagnóstico e, para
 * cada um, a imagem correspondente (getImagemDoRegistro). A API já
 * devolve `url_imagem` dentro do próprio item, então a segunda chamada
 * deixou de existir. O endpoint gera uma signed URL por imagem (bucket
 * privado, ver infra/supabase/storage_policies.md), com validade curta:
 * ela serve para exibir agora, não para guardar.
 *
 * A URL pode vir nula quando a geração falha no Supabase. A lista NÃO
 * pode quebrar por causa disso, então nulo é propagado e cada tela
 * mostra seu próprio placeholder visual.
 *
 * TRADUÇÃO DE NOMES, igual a services/leituras.ts: a API usa os nomes do
 * banco (classe_prevista, criado_em, device_id) e as telas usam os
 * nomes antigos (classificacao, timestamp, dispositivo_id). A conversão
 * fica aqui, num lugar só. `classificacao` já sai traduzido para texto
 * legível por src/domain/doencas.ts, e `classe` guarda o nome técnico
 * para quem precisar comparar sem depender do rótulo.
 */

import { get } from './api';
import { ehSaudavel, rotuloDaClasse } from '../domain/doencas';

/** Janela padrão: 7 dias. Mesma de services/leituras.ts, para o
 * Histórico mostrar leitura e diagnóstico do mesmo período. Sem filtro
 * a API devolve até 1000 itens, muito mais do que cabe numa tela. */
const JANELA_PADRAO_HORAS = 168;

/** Quantos itens a tela de Diagnóstico pede.
 *
 * Não é só economia de banda: a API gera uma signed URL por imagem, e
 * cada uma é uma chamada de rede ao Supabase. Com captura a cada 2h, a
 * janela de 7 dias dá cerca de 84 imagens, logo 84 idas ao Supabase
 * para montar uma tela que mostra o diagnóstico atual e uma fileira de
 * miniaturas. Doze cobre a fileira com folga. */
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
    timestamp: bruto.criado_em,
  };
}

/**
 * Diagnósticos da janela informada, do mais recente para o mais antigo.
 *
 * A API já devolve nessa ordem, mas a ordenação é repetida aqui de
 * propósito: as telas assumem que o item [0] é o diagnóstico atual, e
 * esse contrato não pode depender da cláusula ORDER BY de outro
 * repositório.
 */
export async function getDiagnosticos(
  horas: number = JANELA_PADRAO_HORAS,
  limite?: number,
): Promise<Diagnostico[]> {
  const parametros = new URLSearchParams({ horas: String(horas) });
  if (limite !== undefined) parametros.set('limite', String(limite));

  const brutos = await get<DiagnosticoDaApi[]>(`/diagnosticos?${parametros}`);
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
