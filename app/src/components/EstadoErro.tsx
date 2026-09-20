/**
 * app/src/components/EstadoErro.tsx
 *
 * Estado de erro em tela cheia, usado quando a carga inicial de uma
 * tela falha (ainda não há nenhum dado pra mostrar). Ícone + mensagem
 * + botão "Tentar novamente", no mesmo padrão visual em todas as
 * telas do app.
 */

import React from 'react';
import { View, Text, Pressable, ActivityIndicator, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface EstadoErroProps {
  mensagem: string;
  aoTentarNovamente: () => void;
  tentandoNovamente?: boolean;
}

export function EstadoErro({ mensagem, aoTentarNovamente, tentandoNovamente }: EstadoErroProps) {
  return (
    <View style={styles.container}>
      <Ionicons name="cloud-offline-outline" size={40} color={colors.textMuted} />
      <Text style={styles.mensagem}>{mensagem}</Text>
      <Pressable style={styles.botao} onPress={aoTentarNovamente} disabled={tentandoNovamente}>
        {tentandoNovamente ? (
          <ActivityIndicator size="small" color={colors.oliveGreen} />
        ) : (
          <Text style={styles.botaoTexto}>Tentar novamente</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
    paddingHorizontal: 32,
    gap: 12,
  },
  mensagem: {
    textAlign: 'center',
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },
  botao: {
    marginTop: 8,
    borderWidth: 1.5,
    borderColor: colors.oliveGreen,
    borderRadius: 24,
    paddingHorizontal: 22,
    paddingVertical: 10,
    minWidth: 160,
    alignItems: 'center',
  },
  botaoTexto: {
    color: colors.oliveGreen,
    fontWeight: '700',
    fontSize: 13,
  },
});
