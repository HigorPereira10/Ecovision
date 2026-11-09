/**
 * Helper central de formatação monetária (pt-BR), usado por qualquer
 * tela que exiba valores em Real. Evita repetir a mesma lógica de
 * formatação em vários componentes (Financeiro, Histórico, etc.).
 */

export function formatarMoeda(valor: number): string {
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

export function formatarDataHora(isoString: string): string {
  const data = new Date(isoString);
  const dataFormatada = data.toLocaleDateString('pt-BR');
  const horaFormatada = data.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  return `${dataFormatada}, ${horaFormatada}`;
}