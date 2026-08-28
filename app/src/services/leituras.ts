import leituraMock from '../mocks/leituras.json';

export interface LeituraAmbiental {
  id: number;
  dispositivo_id: number;
  temperatura: number;
  umidade_ar: number;
  umidade_solo: number;
  timestamp: string;
}

function ordenarPorData(leituras: LeituraAmbiental[], crescente: boolean) {
  return [...leituras].sort((a, b) => {
    const diff = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    return crescente ? diff : -diff;
  });
}

/** Retorna a leitura ambiental mais recente. */
export async function getUltimaLeitura(): Promise<LeituraAmbiental | null> {
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
  const leituras = leituraMock as LeituraAmbiental[];
  return ordenarPorData(leituras, true);
}