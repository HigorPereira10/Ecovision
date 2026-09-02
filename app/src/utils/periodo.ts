/**
 * app/src/utils/periodo.ts
 *
 * Opções de filtro por período, usadas tanto na tela de Histórico
 * quanto (futuramente) em qualquer outra lista com timestamp.
 */

export interface OpcaoPeriodo {
  valor: string;
  rotulo: string;
  horas: number | null; // null = todo o período, sem corte
}

export const OPCOES_PERIODO: OpcaoPeriodo[] = [
  { valor: '24h', rotulo: 'Últimas 24h', horas: 24 },
  { valor: '48h', rotulo: 'Últimas 48h', horas: 48 },
  { valor: '7d', rotulo: 'Últimos 7 dias', horas: 24 * 7 },
  { valor: '30d', rotulo: 'Últimos 30 dias', horas: 24 * 30 },
  { valor: 'todos', rotulo: 'Todo o período', horas: null },
];

export function filtrarPorPeriodo<T>(
  itens: T[],
  obterTimestamp: (item: T) => string,
  horas: number | null
): T[] {
  if (horas === null) return itens;
  const limite = Date.now() - horas * 60 * 60 * 1000;
  return itens.filter((item) => new Date(obterTimestamp(item)).getTime() >= limite);
}