/**
 * app/src/components/ResumoFinanceiroCard.tsx
 *
 * Card verde escuro no topo da tela Financeiro: total gasto com insumos
 * e quantidade de lançamentos, no mesmo estilo dos cards de destaque
 * usados no restante do app.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';
import { formatarMoeda } from '../utils/formatarMoeda';

interface Props {
  totalGasto: number;
  quantidadeLancamentos: number;
}

export function ResumoFinanceiroCard({ totalGasto, quantidadeLancamentos }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>Total gasto com insumos</Text>
      <Text style={styles.valor}>{formatarMoeda(totalGasto)}</Text>
      <Text style={styles.subtitulo}>
        {quantidadeLancamentos} lançamento{quantidadeLancamentos !== 1 ? 's' : ''} · dados de demonstração
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.darkGreen,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
  },
  label: {
    color: colors.textOnDark,
    fontSize: 13,
  },
  valor: {
    color: colors.white,
    fontSize: 28,
    fontWeight: '700',
    marginTop: 4,
  },
  subtitulo: {
    color: colors.textOnDark,
    fontSize: 12,
    marginTop: 8,
  },
});