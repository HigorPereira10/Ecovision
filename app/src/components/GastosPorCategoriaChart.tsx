/**
 * Gráfico de barras (victory-native@36.9.2) mostrando o total gasto por
 * categoria. Segue o mesmo padrão de card branco usado no
 * SerieTemporalCard do Dashboard.
 */

import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryChart, VictoryBar, VictoryAxis, VictoryTheme } from 'victory-native';
import { colors } from '../theme/colors';
import { corDaCategoria } from '../theme/categoriaCores';
import { ResumoPorCategoria } from '../services/gastos';

interface Props {
  porCategoria: ResumoPorCategoria[];
}

const larguraTela = Dimensions.get('window').width;

export function GastosPorCategoriaChart({ porCategoria }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Gastos por categoria</Text>

      <VictoryChart
        theme={VictoryTheme.material}
        width={larguraTela - 56}
        height={220}
        domainPadding={{ x: 24 }}
      >
        <VictoryAxis
          style={{
            tickLabels: { fontSize: 10, fill: colors.textMuted },
            axis: { stroke: colors.textMuted },
            grid: { stroke: 'transparent' },
          }}
        />
        <VictoryAxis
          dependentAxis
          style={{
            tickLabels: { fontSize: 10, fill: colors.textMuted },
            axis: { stroke: 'transparent' },
            grid: { stroke: colors.cream },
          }}
        />
        <VictoryBar
          data={porCategoria.map((c) => ({ x: c.categoria, y: c.total }))}
          style={{
            data: {
              fill: ({ datum }) => corDaCategoria(datum.x),
              width: 22,
            },
          }}
          cornerRadius={{ top: 3 }}
        />
      </VictoryChart>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  titulo: {
    color: colors.textDark,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 8,
  },
});