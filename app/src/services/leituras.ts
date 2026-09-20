/**
 * app/src/services/leituras.ts
 *
 * Camada de dados para leituras ambientais (temperatura, umidade do ar,
 * umidade do solo). Hoje lê do mock local (src/mocks/leituras.json); no
 * futuro vira fetch() para o FastAPI (GET /leituras). Mesma assinatura
 * async/Promise usada nos demais serviços, pra troca sem refatorar a tela.
 *
 * Pequeno delay simulado abaixo (mesma técnica já usada em
 * services/alertas.ts) só pra a latência do mock não ficar
 * instantânea — assim os estados de loading das telas que consomem
 * este serviço (Dashboard, Histórico) ficam visíveis e testáveis
 * mesmo antes da API real existir.
 */

import leituraMock from '../mocks/leituras.json';

export interface LeituraAmbiental {
  id: number;
  dispositivo_id: number;
  temperatura: number;
  umidade_ar: number;
  umidade_solo: number;
  timestamp: string;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ordenarPorData(leituras: LeituraAmbiental[], crescente: boolean) {
  return [...leituras].sort((a, b) => {
    const diff = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    return crescente ? diff : -diff;
  });
}

/** Retorna a leitura ambiental mais recente. */
export async function getUltimaLeitura(): Promise<LeituraAmbiental | null> {
  await delay(300); // simula latência de rede
  const leituras = leituraMock as LeituraAmbiental[];
  if (!leituras || leituras.length === 0) return null;
  return ordenarPorData(leituras, false)[0];
}

/**
 * Retorna todas as leituras ordenadas cronologicamente (mais antiga primeiro),
 * para uso no gráfico de série temporal.
 * Futuro: vira `await fetch(`${API_URL}/leituras?horas=${horas}`)`.
 */
export async function getHistoricoLeituras(): Promise<LeituraAmbiental[]> {
  await delay(300); // simula latência de rede
  const leituras = leituraMock as LeituraAmbiental[];
  return ordenarPorData(leituras, true);
}
