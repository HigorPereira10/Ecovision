/**
 * Aviso compacto e não-bloqueante, usado quando um pull-to-refresh (ou
 * outra atualização em segundo plano) falha, mas a tela ainda tem os
 * últimos dados válidos pra mostrar. Diferente de EstadoErro (que
 * substitui a tela toda), este aparece como uma faixa no topo do
 * conteúdo existente e some sozinho na próxima atualização bem-sucedida.
 */

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface AvisoErroInlineProps {
  mensagem: string;
  aoTentarNovamente?: () => void;
}

export function AvisoErroInline({ mensagem, aoTentarNovamente }: AvisoErroInlineProps) {
  return (
    <View style={styles.container}>
      <Ionicons name="alert-circle-outline" size={16} color={colors.cuidado} />
      <Text style={styles.texto}>{mensagem}</Text>
      {aoTentarNovamente && (
        <Pressable onPress={aoTentarNovamente} hitSlop={8}>
          <Text style={styles.link}>Tentar novamente</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: colors.white,
    borderRadius: 10,
    borderLeftWidth: 3,
    borderLeftColor: colors.cuidado,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 12,
  },
  texto: {
    flex: 1,
    fontSize: 12,
    color: colors.textDark,
  },
  link: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.oliveGreen,
  },
});
