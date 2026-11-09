/**
 * Aviso leve de ação concluída (por exemplo, "Gasto salvo"), exibido no
 * rodapé e ocultado após alguns segundos, com Animated. Controlado pelo
 * hook useToastSucesso.
 */

import React, { useEffect, useRef } from 'react';
import { Animated, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface ToastSucessoProps {
  mensagem: string | null;
}

export function ToastSucesso({ mensagem }: ToastSucessoProps) {
  const opacidade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacidade, {
      toValue: mensagem ? 1 : 0,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }, [mensagem]);

  if (!mensagem) return null;

  return (
    <Animated.View style={[styles.container, { opacity: opacidade }]} pointerEvents="none">
      <Ionicons name="checkmark-circle" size={18} color={colors.white} />
      <Text style={styles.texto}>{mensagem}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 24,
    left: 20,
    right: 20,
    backgroundColor: colors.darkGreen,
    borderRadius: 24,
    paddingVertical: 12,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  texto: {
    color: colors.white,
    fontSize: 13,
    fontWeight: '600',
    flexShrink: 1,
  },
});