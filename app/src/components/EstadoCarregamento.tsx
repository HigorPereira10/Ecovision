/**
 * Spinner de carregamento padrão, usado em tela cheia enquanto a
 * primeira busca de dados de uma tela ainda não terminou. Substitui
 * os blocos de ActivityIndicator que estavam duplicados em cada tela.
 */

import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

interface EstadoCarregamentoProps {
  mensagem?: string;
}

export function EstadoCarregamento({ mensagem }: EstadoCarregamentoProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={colors.oliveGreen} />
      {mensagem && <Text style={styles.mensagem}>{mensagem}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
    gap: 12,
  },
  mensagem: {
    fontSize: 13,
    color: colors.textMuted,
  },
});
