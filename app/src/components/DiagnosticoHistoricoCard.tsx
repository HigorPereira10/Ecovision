/**
 * Card de diagnóstico na lista do Histórico: imagem (ou placeholder),
 * data, classificação (verde para sadia, vermelho para doença) e
 * confiança.
 *
 * A imagem e o rótulo vêm prontos no objeto Diagnostico, resolvidos em
 * services/diagnosticos.ts. Este componente não normaliza texto nem
 * decide o que é "saudável": antes ele fazia isso por conta própria,
 * com uma segunda cópia da mesma regra que a tela de Diagnóstico já
 * tinha. Duas cópias da mesma decisão divergem na primeira vez que
 * alguém mexe em uma delas. A regra única está em src/domain/doencas.ts.
 */

import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { corDoDiagnostico } from '../theme/coresDiagnostico';
import { Diagnostico } from '../services/diagnosticos';

interface Props {
  diagnostico: Diagnostico;
}

export function DiagnosticoHistoricoCard({ diagnostico }: Props) {
  const dataFormatada = new Date(diagnostico.timestamp).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <View style={styles.card}>
      {diagnostico.urlImagem ? (
        <Image source={{ uri: diagnostico.urlImagem }} style={styles.imagem} />
      ) : (
        <View style={[styles.imagem, styles.imagemPlaceholder]}>
          <Ionicons name="leaf-outline" size={22} color={colors.oliveGreen} />
        </View>
      )}

      <View style={styles.info}>
        <Text style={styles.data}>{dataFormatada}</Text>
        <Text
          style={[
            styles.classificacao,
            { color: corDoDiagnostico(diagnostico) },
          ]}
        >
          {diagnostico.classificacao}
        </Text>
      </View>

      {/* Sem diagnóstico não existe confiança: mostrar "0%" sugeriria
          uma análise que deu quase certeza de nada, quando na verdade
          análise nenhuma foi feita. */}
      {!diagnostico.semDiagnostico && (
        <Text style={styles.confianca}>{Math.round(diagnostico.confianca * 100)}%</Text>
      )}
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