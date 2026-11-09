/**
 * Cor de cada categoria de gasto, sempre a partir da paleta de colors.ts.
 */

import { colors } from './colors';

export const CATEGORIA_COR: Record<string, string> = {
  Fungicida: colors.danger,
  Fertilizante: colors.oliveGreen,
  'Mão de obra': colors.informativo,
  Energia: colors.cuidado,
  Sementes: colors.darkGreen,
  Outro: colors.textMuted,
};

export function corDaCategoria(categoria: string): string {
  return CATEGORIA_COR[categoria] || colors.textMuted;
}