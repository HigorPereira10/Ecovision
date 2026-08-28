import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

interface LeituraCardProps {
  titulo: string;
  valor: number;
  unidade: string;
  icone?: string;
}

export function LeituraCard({ titulo, valor, unidade, icone }: LeituraCardProps) {
  return (
    <View style={styles.card}>
      {icone && <Text style={styles.icone}>{icone}</Text>}
      <Text style={styles.valor}>
        {valor.toFixed(1)}
        <Text style={styles.unidade}>{unidade}</Text>
      </Text>
      <Text style={styles.titulo}>{titulo}</Text>
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
    fontSize: 20,
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
    color: colors.textMuted,
    marginTop: 2,
  },
});