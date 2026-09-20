/**
 * app/src/theme/categoriaCores.ts
 *
 * Mapeia cada categoria de gasto a uma cor já existente em colors.ts.
 * Mantém a regra do projeto de nunca inventar hex novo dentro de
 * componentes — tudo sai da paleta central.
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