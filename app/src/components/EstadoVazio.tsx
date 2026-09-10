/**
 * app/src/components/EstadoVazio.tsx
 *
 * Estado vazio padronizado, usado sempre que uma lista/seção não tem
 * dados pra mostrar (ex: "nenhum alerta ainda", "nenhum gasto neste
 * mês"). Duas variantes:
 * - "tela" (padrão): ocupa a tela toda, centralizado — quando é o
 *   único conteúdo da tela (ex: Diagnóstico sem nenhum registro).
 * - "secao": versão compacta, pra usar dentro de uma ScrollView junto
 *   com outros blocos (ex: Histórico, onde só uma sub-lista está vazia).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface EstadoVazioProps {
  icone?: keyof typeof Ionicons.glyphMap;
  titulo: string;
  subtitulo?: string;
  variante?: 'tela' | 'secao';
}

export function EstadoVazio({
  icone = 'file-tray-outline',
  titulo,
  subtitulo,
  variante = 'tela',
}: EstadoVazioProps) {
  const compacto = variante === 'secao';
  return (
    <View style={[styles.container, compacto && styles.containerCompacto]}>
      <Ionicons name={icone} size={compacto ? 26 : 40} color={colors.textMuted} />
      <Text style={[styles.titulo, compacto && styles.tituloCompacto]}>{titulo}</Text>
      {subtitulo && <Text style={styles.subtitulo}>{subtitulo}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
    paddingHorizontal: 32,
    gap: 8,
  },
  containerCompacto: {
    flex: 0,
    paddingVertical: 22,
    paddingHorizontal: 16,
    backgroundColor: colors.white,
    borderRadius: 12,
    marginBottom: 12,
  },
  titulo: {
    textAlign: 'center',
    color: colors.textDark,
    fontSize: 14,
    fontWeight: '600',
    marginTop: 4,
  },
  tituloCompacto: {
    fontSize: 13,
    fontWeight: '600',
  },
  subtitulo: {
    textAlign: 'center',
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
  },
});