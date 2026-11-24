/**
 * Leituras ambientais (temperatura, umidade do ar e umidade do solo), a
 * partir de GET /leituras.
 *
 * Converte os nomes da API (temperatura_c, umidade_ar_pct,
 * umidade_solo_pct, criado_em) para os usados pelas telas (temperatura,
 * umidade_ar, umidade_solo, timestamp). A lista reúne as leituras de 15
 * minutos e as dos ciclos de captura, distinguidas por `temFoto`.
 *
 * Os valores podem vir nulos quando um sensor falha e são mantidos como
 * null, nunca 0, que seria lido como medição; os gráficos ignoram esses
 * pontos.
 */

import { get } from './api';

/** Janela padrão do histórico: 7 dias (a cada 2h, cerca de 84 leituras).
 * Sem esse filtro a API devolve até 1000 registros, cerca de 3 meses de
 * dados, muito mais do que faz sentido carregar numa tela de celular. */
const JANELA_PADRAO_HORAS = 168;

/** Formato devolvido pela API (GET /leituras). */
interface LeituraDaApi {
  id: number;
  device_id: string;
  temperatura_c: number | null;
  umidade_ar_pct: number | null;
  umidade_solo_pct: number | null;
  tem_foto: boolean;
  criado_em: string;
}

export interface LeituraAmbiental {
  id: number;
  dispositivo_id: string;
  temperatura: number | null;
  umidade_ar: number | null;
  umidade_solo: number | null;
  /** true quando a leitura veio de um ciclo de captura, com foto. */
  temFoto: boolean;
  timestamp: string;
}

function traduzir(bruta: LeituraDaApi): LeituraAmbiental {
  return {
    id: bruta.id,
    dispositivo_id: bruta.device_id,
    temperatura: bruta.temperatura_c,
    umidade_ar: bruta.umidade_ar_pct,
    umidade_solo: bruta.umidade_solo_pct,
    // ?? false mantém compatibilidade com versões da API sem este campo.
    temFoto: bruta.tem_foto ?? false,
    timestamp: bruta.criado_em,
  };
}

function ordenarPorData(leituras: LeituraAmbiental[], crescente: boolean) {
  return [...leituras].sort((a, b) => {
    const diff = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    return crescente ? diff : -diff;
  });
}

/** Com `horas` null, sem corte de período: a API devolve as últimas 1000. */
async function buscar(horas: number | null): Promise<LeituraAmbiental[]> {
  const brutas = await get<LeituraDaApi[]>(horas === null ? '/leituras' : `/leituras?horas=${horas}`);
  return brutas.map(traduzir);
}

/** Retorna a leitura ambiental mais recente, ou null se não houver nenhuma. */
export async function getUltimaLeitura(): Promise<LeituraAmbiental | null> {
  // Janela curta de propósito: para o "agora" do Dashboard não faz
  // sentido baixar a semana inteira e descartar quase tudo.
  const leituras = await buscar(24);
  if (leituras.length === 0) return null;
  return ordenarPorData(leituras, false)[0];
}

/**
 * Leituras da janela padrão, em ordem cronológica, para os gráficos.
 */
export async function getHistoricoLeituras(
  horas: number | null = JANELA_PADRAO_HORAS,
): Promise<LeituraAmbiental[]> {
  return ordenarPorData(await buscar(horas), true);
}
