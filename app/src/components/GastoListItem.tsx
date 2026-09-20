/**
 * app/src/components/GastoListItem.tsx
 *
 * Linha individual da lista "Transações recentes": ícone, descrição,
 * categoria + data, valor em destaque e botão de excluir.
 */

import React from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { formatarMoeda, formatarDataHora } from '../utils/formatarMoeda';
import { Gasto } from '../services/gastos';

interface Props {
  gasto: Gasto;
  onExcluir?: () => void;
  excluindo?: boolean;
}

export function GastoListItem({ gasto, onExcluir, excluindo = false }: Props) {
  return (
    <View style={[styles.linha, excluindo && styles.linhaExcluindo]}>
      <View style={styles.iconeCirculo}>
        <Ionicons name="cart-outline" size={18} color={colors.oliveGreen} />
      </View>

      <View style={styles.info}>
        <Text style={styles.descricao}>{gasto.descricao}</Text>
        <Text style={styles.detalhe}>
          {gasto.categoria} · {formatarDataHora(gasto.data)}
        </Text>
      </View>

      <Text style={styles.valor}>- {formatarMoeda(gasto.valor)}</Text>

      {onExcluir && (
        <Pressable
          onPress={onExcluir}
          disabled={excluindo}
          hitSlop={10}
          style={styles.botaoExcluir}
        >
          {excluindo ? (
            <ActivityIndicator size="small" color={colors.textMuted} />
          ) : (
            <Ionicons name="trash-outline" size={18} color={colors.textMuted} />
          )}
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  linha: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
  },
  linhaExcluindo: {
    opacity: 0.6,
  },
  iconeCirculo: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.cream,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  info: {
    flex: 1,
  },
  descricao: {
    color: colors.textDark,
    fontSize: 14,
    fontWeight: '600',
  },
  detalhe: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  valor: {
    color: colors.danger,
    fontSize: 14,
    fontWeight: '700',
  },
  botaoExcluir: {
    marginLeft: 12,
    width: 28,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
