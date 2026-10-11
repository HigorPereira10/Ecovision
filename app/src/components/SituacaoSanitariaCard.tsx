import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { VictoryPie } from 'victory-native';
import { colors } from '../theme/colors';

interface SituacaoSanitariaCardProps {
  saudaveis: number;
  comDoenca: number;
}

/** O subtítulo descreve a AMOSTRA, não uma janela de tempo.
 *
 * Ele dizia "Diagnósticos das últimas 48 horas", com 48 fixo no código,
 * enquanto a busca real era de outra janela. O número no texto e o
 * número na consulta viviam em arquivos diferentes e, na primeira vez
 * que a consulta mudou, o rótulo passou a mentir sem que nada quebrasse.
 *
 * Contar o que está no próprio card elimina a possibilidade: seja qual
 * for a janela que services/diagnosticos.ts usar amanhã, esta frase
 * continua verdadeira. */
function descreverAmostra(total: number): string {
  if (total === 0) return 'Nenhum diagnóstico recebido ainda';
  if (total === 1) return 'Baseado no último diagnóstico';
  return `Baseado nos ${total} diagnósticos mais recentes`;
}

export function SituacaoSanitariaCard({
  saudaveis,
  comDoenca,
}: SituacaoSanitariaCardProps) {
  const total = saudaveis + comDoenca;
  const data =
    total > 0
      ? [
          { x: 'Saudáveis', y: saudaveis },
          { x: 'Com doença', y: comDoenca },
        ]
      : [{ x: 'Sem dados', y: 1 }];

  const cores = total > 0 ? [colors.oliveGreen, colors.danger] : ['#E0E0E0'];

  return (
    <View style={styles.card}>
      <Text style={styles.titulo}>Situação sanitária</Text>
      <Text style={styles.subtitulo}>{descreverAmostra(total)}</Text>

      <View style={styles.graficoContainer}>
        <VictoryPie
          data={data}
          colorScale={cores}
          innerRadius={70}
          labels={() => null}
          width={220}
          height={220}
          padding={10}
        />
      </View>

      <View style={styles.legendaContainer}>
        <View style={styles.legendaItem}>
          <View style={[styles.dot, { backgroundColor: colors.oliveGreen }]} />
          <Text style={styles.legendaTexto}>Saudáveis ({saudaveis})</Text>
        </View>
        <View style={styles.legendaItem}>
          <View style={[styles.dot, { backgroundColor: colors.danger }]} />
          <Text style={styles.legendaTexto}>Com doença ({comDoenca})</Text>
        </View>
      </View>
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
    marginBottom: 4,
  },
  graficoContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  legendaContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 8,
    gap: 24,
  },
  legendaItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 6,
  },
  legendaTexto: {
    fontSize: 13,
    color: colors.textDark,
  },
});