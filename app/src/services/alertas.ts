/**
 * app/src/services/alertas.ts
 *
 * Camada de dados para o painel de Alertas. Hoje lê do mock local
 * (src/mocks/alertas.json); no futuro vira fetch() para o FastAPI
 * (GET /alertas e PATCH /alertas/{id}/lido). Mesma assinatura
 * async/Promise usada em services/leituras.ts e services/diagnosticos.ts,
 * pra troca sem refatorar a tela.
 *
 * TODO quando a API estiver pronta:
 * - getAlertas() vira `await api.get('/alertas')` (usando o cliente
 *   central de services/api.ts, já autenticado via JWT).
 * - marcarAlertaLido() vira `await api.patch(`/alertas/${alertaId}/lido`)`.
 * - Como o backend real vai persistir o estado "lido" no Postgres, o
 *   array em memória abaixo deixa de existir — cada chamada a
 *   getAlertas() vai refletir o estado já atualizado no servidor.
 */

import alertasMock from '../mocks/alertas.json';

export type SeveridadeAlerta = 'critico' | 'cuidado' | 'informativo';

export interface Alerta {
  id: number;
  tipo: string;
  severidade: SeveridadeAlerta;
  titulo: string;
  descricao: string;
  lido: boolean;
  timestamp: string;
}

// Cópia mutável em memória do mock, pra simular persistência do estado
// "lido" entre chamadas dentro da mesma sessão do app (o JSON importado
// é somente leitura). Isso deixa de existir quando marcarAlertaLido()
// virar uma chamada PATCH real — o backend passa a ser a fonte da verdade.
let alertasEmMemoria: Alerta[] = [...(alertasMock as Alerta[])];

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ordenarPorDataDesc(alertas: Alerta[]): Alerta[] {
  return [...alertas].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
}

/**
 * Retorna todos os alertas, do mais recente para o mais antigo.
 * Futuro: `await fetch(`${API_URL}/alertas`, { headers: authHeader })`.
 */
export async function getAlertas(): Promise<Alerta[]> {
  await delay(300); // simula latência de rede
  return ordenarPorDataDesc(alertasEmMemoria);
}

/**
 * Marca um alerta específico como lido.
 * Futuro: `await fetch(`${API_URL}/alertas/${alertaId}/lido`, { method: 'PATCH', headers: authHeader })`.
 */
export async function marcarAlertaLido(alertaId: number): Promise<void> {
  await delay(200);

  const index = alertasEmMemoria.findIndex((alerta) => alerta.id === alertaId);
  if (index === -1) {
    throw new Error(`Alerta com id ${alertaId} não encontrado.`);
  }

  alertasEmMemoria[index] = { ...alertasEmMemoria[index], lido: true };
}

/**
 * Retorna a contagem de alertas não lidos.
 * Útil pra um badge na tab bar ou no header, se quiser adicionar depois.
 */
export async function getContagemNaoLidos(): Promise<number> {
  await delay(100);
  return alertasEmMemoria.filter((alerta) => !alerta.lido).length;
}