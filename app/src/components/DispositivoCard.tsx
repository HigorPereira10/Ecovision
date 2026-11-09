import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { Dispositivo } from '../services/dispositivos';

/**
 * Cartão de um dispositivo na tela de Perfil. Os limiares são exibidos
 * pelo efeito ("Alerta de calor") e pelo sentido da comparação ("acima de
 * 34 °C"): temperatura e umidade do ar são limites superiores, e umidade
 * do solo é limite inferior. São os mesmos valores que geram os alertas.
 */

interface Props {
  dispositivo: Dispositivo;
}

export function DispositivoCard({ dispositivo }: Props) {
  const ativo = dispositivo.status === 'ativo';

  return (
    <View style={styles.card}>
      <View style={styles.linhaTitulo}>
        <View style={styles.tituloComIcone}>
          <Ionicons name="hardware-chip-outline" size={18} color={colors.darkGreen} />
          <Text style={styles.nome}>{dispositivo.nome}</Text>
        </View>
        <View style={[styles.badge, { backgroundColor: ativo ? colors.oliveGreen : colors.informativo }]}>
          <Text style={styles.badgeTexto}>{ativo ? 'ativo' : 'inativo'}</Text>
        </View>
      </View>

      <View style={styles.linhaLocal}>
        <Ionicons name="location-outline" size={14} color={colors.textMuted} />
        <Text style={styles.local}>
          {dispositivo.campo} · {dispositivo.setor}
        </Text>
      </View>

      <View style={styles.grid}>
        <View style={styles.coluna}>
          <Text style={styles.label}>Intervalo de captura</Text>
          <Text style={styles.valor}>
            {dispositivo.intervalo_captura_min !== null
              ? `${dispositivo.intervalo_captura_min} min`
              : 'Não informado'}
          </Text>
        </View>
        <View style={styles.coluna}>
          <Text style={styles.label}>Alerta de calor</Text>
          <Text style={styles.valor}>acima de {dispositivo.limiar_temperatura} °C</Text>
        </View>
      </View>

      <View style={styles.grid}>
        <View style={styles.coluna}>
          <Text style={styles.label}>Alerta de mofo</Text>
          <Text style={styles.valor}>
            ar acima de {dispositivo.limiar_umidade_ar}%
          </Text>
        </View>
        <View style={styles.coluna}>
          <Text style={styles.label}>Alerta de solo seco</Text>
          <Text style={styles.valor}>
            abaixo de {dispositivo.limiar_umidade_solo}%
          </Text>
        </View>
      </View>

      <Text style={styles.rodape}>
        Quando uma medição cruza um destes limites, o aviso aparece na tela de
        Alertas.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  linhaTitulo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  tituloComIcone: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexShrink: 1,
  },
  nome: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textDark,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  badgeTexto: {
    color: colors.white,
    fontSize: 12,
    fontWeight: '600',
  },
  linhaLocal: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
    marginBottom: 12,
  },
  local: {
    fontSize: 13,
    color: colors.textMuted,
  },
  grid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  coluna: {
    flex: 1,
  },
  label: {
    fontSize: 12,
    color: colors.textMuted,
    marginBottom: 2,
  },
  valor: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textDark,
  },
  rodape: {
    fontSize: 11,
    color: colors.textMuted,
    fontStyle: 'italic',
    marginTop: 2,
    lineHeight: 15,
  },
});