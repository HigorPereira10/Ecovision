import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface LeituraCardProps {
  titulo: string;
  /** Nulo quando o sensor falhou naquele ciclo: a API devolve null e o
   * card mostra um traço, nunca 0 (que seria uma medição válida e
   * alarmante, ex.: "0% de umidade do solo"). */
  valor: number | null;
  unidade: string;
  icone: keyof typeof Ionicons.glyphMap;
  cor: string;
}

export function LeituraCard({ titulo, valor, unidade, icone, cor }: LeituraCardProps) {
  const semLeitura = valor === null;

  return (
    <View style={styles.card}>
      <Ionicons name={icone} size={20} color={cor} style={styles.icone} />
      <Text style={[styles.valor, semLeitura && styles.valorAusente]}>
        {semLeitura ? '--' : valor.toFixed(1)}
        <Text style={styles.unidade}>{unidade}</Text>
      </Text>
      <Text style={[styles.titulo, { color: cor }]}>{titulo}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 16,
    paddingVertical: 16,
    marginHorizontal: 4,
    alignItems: 'center',
  },
  icone: {
    marginBottom: 4,
  },
  valor: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.textDark,
  },
  valorAusente: {
    color: colors.textMuted,
  },
  unidade: {
    fontSize: 13,
    fontWeight: '400',
    color: colors.textMuted,
  },
  titulo: {
    fontSize: 12,
    fontWeight: '600',
    marginTop: 2,
  },
});