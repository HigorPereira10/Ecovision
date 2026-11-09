/**
 * Chip de filtro reutilizável (ícone + rótulo + seta) que abre um menu
 * modal simples com as opções. Usado no Histórico para período e campo,
 * mas serve pra qualquer filtro single-select futuro.
 */

import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Modal, FlatList, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

export interface OpcaoFiltro {
  valor: string;
  rotulo: string;
}

interface FiltroDropdownProps {
  icone: keyof typeof Ionicons.glyphMap;
  opcoes: OpcaoFiltro[];
  valorSelecionado: string;
  onSelecionar: (valor: string) => void;
}

export function FiltroDropdown({
  icone,
  opcoes,
  valorSelecionado,
  onSelecionar,
}: FiltroDropdownProps) {
  const [aberto, setAberto] = useState(false);
  const rotuloAtual =
    opcoes.find((o) => o.valor === valorSelecionado)?.rotulo ?? opcoes[0]?.rotulo ?? '';

  return (
    <>
      <TouchableOpacity style={styles.chip} onPress={() => setAberto(true)} activeOpacity={0.7}>
        <Ionicons name={icone} size={16} color={colors.oliveGreen} style={styles.chipIcone} />
        <Text style={styles.chipTexto} numberOfLines={1}>
          {rotuloAtual}
        </Text>
        <Ionicons name="chevron-down" size={16} color={colors.textMuted} />
      </TouchableOpacity>

      <Modal visible={aberto} transparent animationType="fade" onRequestClose={() => setAberto(false)}>
        <TouchableOpacity
          style={styles.overlay}
          activeOpacity={1}
          onPress={() => setAberto(false)}
        >
          <View style={styles.menu}>
            <FlatList
              data={opcoes}
              keyExtractor={(item) => item.valor}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.opcao}
                  onPress={() => {
                    onSelecionar(item.valor);
                    setAberto(false);
                  }}
                >
                  <Text
                    style={[
                      styles.opcaoTexto,
                      item.valor === valorSelecionado && styles.opcaoTextoAtivo,
                    ]}
                  >
                    {item.rotulo}
                  </Text>
                  {item.valor === valorSelecionado && (
                    <Ionicons name="checkmark" size={18} color={colors.oliveGreen} />
                  )}
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    flex: 1,
  },
  chipIcone: { marginRight: 6 },
  chipTexto: {
    flex: 1,
    color: colors.textDark,
    fontSize: 13,
    fontWeight: '600',
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  menu: {
    backgroundColor: colors.white,
    borderRadius: 12,
    maxHeight: 320,
    paddingVertical: 6,
  },
  opcao: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  opcaoTexto: { fontSize: 14, color: colors.textDark },
  opcaoTextoAtivo: { color: colors.oliveGreen, fontWeight: '700' },
});