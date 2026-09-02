/**
 * app/src/components/DiagnosticoHistoricoCard.tsx
 *
 * Card de diagnóstico na lista do Histórico: imagem (ou placeholder),
 * data, classificação (colorida por saudável/doente) e confiança.
 */

import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { Diagnostico } from '../services/diagnosticos';

interface Props {
  diagnostico: Diagnostico;
  caminhoImagem: string | null;
}

function ehSaudavel(classificacao: string): boolean {
  return classificacao
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .includes('saudavel');
}

export function DiagnosticoHistoricoCard({ diagnostico, caminhoImagem }: Props) {
  const saudavel = ehSaudavel(diagnostico.classificacao);
  const dataFormatada = new Date(diagnostico.timestamp).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <View style={styles.card}>
      {caminhoImagem ? (
        <Image source={{ uri: caminhoImagem }} style={styles.imagem} />
      ) : (
        <View style={[styles.imagem, styles.imagemPlaceholder]}>
          <Ionicons name="leaf-outline" size={22} color={colors.oliveGreen} />
        </View>
      )}

      <View style={styles.info}>
        <Text style={styles.data}>{dataFormatada}</Text>
        <Text
          style={[styles.classificacao, { color: saudavel ? colors.oliveGreen : colors.danger }]}
        >
          {diagnostico.classificacao}
        </Text>
      </View>

      <Text style={styles.confianca}>{Math.round(diagnostico.confianca * 100)}%</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 10,
    marginBottom: 10,
  },
  imagem: { width: 48, height: 48, borderRadius: 8, marginRight: 12 },
  imagemPlaceholder: {
    backgroundColor: colors.cream,
    justifyContent: 'center',
    alignItems: 'center',
  },
  info: { flex: 1 },
  data: { fontSize: 12, color: colors.textMuted, marginBottom: 2 },
  classificacao: { fontSize: 14, fontWeight: '700' },
  confianca: { fontSize: 14, fontWeight: '700', color: colors.textDark },
});