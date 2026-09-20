/**
 * app/src/components/UmidadeBarChart.tsx
 *
 * Gráfico de barras (umidade do solo por leitura) da tela de Histórico.
 * Usa victory-native@36.9.2, mesma versão já resolvida no projeto
 * (v42 é incompatível com react-native-worklets@0.5.1).
 */

import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { VictoryChart, VictoryBar, VictoryAxis, VictoryTheme } from 'victory-native';
import { colors } from '../theme/colors';
import { LeituraAmbiental } from '../services/leituras';

interface Props {
  leituras: LeituraAmbiental[];
}

const larguraTela = Dimensions.get('window').width;

export function UmidadeBarChart({ leituras }: Props) {
  const dados = [...leituras]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((l) => ({
      x: new Date(l.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
      y: l.umidade_solo,
    }));

  if (dados.length === 0) {
    return (
      <View style={styles.card}>
        <Text style={styles.titulo}>Umidade registrada</Text>
        <Text style={styles.subtitulo}>Nenhuma leitura no período selecionado.</Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Umidade registrada</Text>
      <Text style={styles.subtitulo}>Solo e ar (%) por leitura</Text>

      <VictoryChart
        theme={VictoryTheme.material}
        width={larguraTela - 24}
        height={200}
        domainPadding={{ x: 14 }}
        padding={{ top: 10, bottom: 40, left: 36, right: 16 }}
      >
        <VictoryAxis
          style={{
            axis: { stroke: colors.textMuted },
            tickLabels: { fontSize: 10, fill: colors.textMuted },
            grid: { stroke: 'transparent' },
          }}
          tickFormat={(t: string, i: number) => (i % 2 === 0 ? t : '')}
        />
        <VictoryAxis
          dependentAxis
          domain={[0, 100]}
          style={{
            axis: { stroke: 'transparent' },
            tickLabels: { fontSize: 10, fill: colors.textMuted },
            grid: { stroke: '#E4E4DC' },
          }}
        />
        <VictoryBar
          data={dados}
          style={{ data: { fill: colors.oliveGreen, width: 14 } }}
          cornerRadius={{ top: 3 }}
        />
      </VictoryChart>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
  },
  titulo: { fontSize: 15, fontWeight: '700', color: colors.textDark },
  subtitulo: { fontSize: 12, color: colors.textMuted, marginBottom: 8 },
});