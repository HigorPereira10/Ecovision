/**
 * app/src/services/leituras.ts
 *
 * Camada de dados para leituras ambientais (temperatura, umidade do ar,
 * umidade do solo). Consome GET /leituras da API real (ver
 * cloud/app/api/routes/historico.py).
 *
 * SERVE DE MODELO para migrar os demais serviços (alertas.ts,
 * diagnosticos.ts, dispositivos.ts, gastos.ts), que ainda leem de
 * src/mocks/. O padrão é: chamar api.get(), traduzir a resposta para a
 * interface que as telas já usam, e manter a assinatura async/Promise.
 *
 * TRADUÇÃO DE NOMES: a API usa os nomes do schema do banco
 * (temperatura_c, umidade_ar_pct, umidade_solo_pct, criado_em) e as
 * telas usam os nomes antigos (temperatura, umidade_ar, umidade_solo,
 * timestamp). A conversão fica aqui, num lugar só, para nenhuma tela
 * precisar mudar.
 *
 * DOIS CRONOGRAMAS, UMA SÉRIE: desde 2026-11-03 o Pi manda leitura de
 * sensor a cada 15 minutos (sem foto, POST /leituras) e captura completa
 * a cada 2 horas (POST /diagnostico). As duas chegam nesta mesma lista,
 * distinguidas por `temFoto`. Antes, leitura só existia junto de uma
 * foto, e a tela inicial exibia temperatura de até 2 horas atrás sem ter
 * nada mais novo para buscar.
 *
 * MEDIÇÃO AUSENTE: os três valores podem vir nulos. Quando um sensor
 * falha, o edge/ grava None naquele campo e segue o ciclo, para não
 * perder a foto por causa de um sensor instável. Nulo é propagado
 * como null de propósito: converter para 0 mostraria "0% de umidade do
 * solo", um valor válido e alarmante, quando na verdade não houve
 * medição. Os gráficos pulam esses pontos.
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
  /** true quando a leitura veio de um ciclo de captura, com foto.
   *
   * Desde 2026-11-03 o Pi tem dois cronogramas: sensor a cada 15 min
   * (POST /leituras) e foto a cada 2 h (POST /diagnostico). As telas
   * desenham as duas igual, porque as medicoes sao as mesmas, mas o
   * campo existe para poder explicar ao produtor por que o numero de
   * pontos de ambiente nao bate com o de diagnosticos. */
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
    // ?? false para o app nao quebrar contra uma API mais antiga, que
    // nao devolvia este campo. Acontece de verdade: o aplicativo
    // atualiza por EAS Update e o backend por deploy no Railway, e nada
    // garante que os dois cheguem na mesma ordem.
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

async function buscar(horas: number): Promise<LeituraAmbiental[]> {
  const brutas = await get<LeituraDaApi[]>(`/leituras?horas=${horas}`);
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
 * Retorna as leituras da janela padrão, ordenadas cronologicamente
 * (mais antiga primeiro), para o gráfico de série temporal.
 */
export async function getHistoricoLeituras(
  horas: number = JANELA_PADRAO_HORAS,
): Promise<LeituraAmbiental[]> {
  return ordenarPorData(await buscar(horas), true);
}
