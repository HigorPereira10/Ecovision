import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface LeituraCardProps {
  titulo: string;
  valor: number;
  unidade: string;
  icone: keyof typeof Ionicons.glyphMap;
  cor: string;
}

export function LeituraCard({ titulo, valor, unidade, icone, cor }: LeituraCardProps) {
  return (
    <View style={styles.card}>
      <Ionicons name={icone} size={20} color={cor} style={styles.icone} />
      <Text style={styles.valor}>
        {valor.toFixed(1)}
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