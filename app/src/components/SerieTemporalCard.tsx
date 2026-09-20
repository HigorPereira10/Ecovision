import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryChart, VictoryLine, VictoryAxis } from 'victory-native';
import { colors } from '../theme/colors';
import { LeituraAmbiental } from '../services/leituras';

interface SerieTemporalCardProps {
  leituras: LeituraAmbiental[]; // ordenadas por timestamp crescente
}

export function SerieTemporalCard({ leituras }: SerieTemporalCardProps) {
  const dadosTemperatura = leituras.map((l) => ({
    x: new Date(l.timestamp),
    y: l.temperatura,
  }));

  const dadosUmidade = leituras.map((l) => ({
    x: new Date(l.timestamp),
    y: l.umidade_ar,
  }));

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Série temporal</Text>
      <Text style={styles.subtitulo}>Temperatura (°C) e umidade do ar (%)</Text>

      <VictoryChart width={Dimensions.get('window').width - 64} height={220}>
        <VictoryAxis
          tickFormat={(t) =>
            new Date(t).toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
            })
          }
          style={{
            tickLabels: { fontSize: 9, fill: colors.textMuted },
            axis: { stroke: colors.textMuted },
          }}
        />
        <VictoryAxis
          dependentAxis
          style={{
            tickLabels: { fontSize: 10, fill: colors.textMuted },
            axis: { stroke: colors.textMuted },
          }}
        />
        <VictoryLine
          data={dadosUmidade}
          style={{ data: { stroke: colors.oliveGreen, strokeWidth: 2 } }}
        />
        <VictoryLine
          data={dadosTemperatura}
          style={{ data: { stroke: colors.danger, strokeWidth: 2 } }}
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
    fontSize: 16,
    fontWeight: '700',
    color: colors.textDark,
  },
  subtitulo: {
    fontSize: 12,
    color: colors.textMuted,
    marginBottom: 8,
  },
});