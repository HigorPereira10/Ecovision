/**
 * app/src/screens/AlertasScreen.tsx
 *
 * Tela de Alertas: lista de alertas mockados, filtráveis por severidade
 * (Crítico / Cuidado / Informativo), com status lido/não lido e ação
 * "Marcar como lido" (estado local por enquanto — troca por
 * PATCH /alertas/{id}/lido quando a API do Higor estiver pronta).
 *
 * Header customizado (logo + título) segue o mesmo padrão do
 * DashboardScreen — a aba "Alertas" no AppNavigator precisa estar com
 * headerShown: false, senão aparecem dois headers sobrepostos (mesmo
 * problema já resolvido no DiagnosticoScreen).
 */

import React, { useState, useMemo } from 'react';
import { View, Text, FlatList, StyleSheet, Pressable, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import alertasMock from '../mocks/alertas.json';
import { colors } from '../theme/colors';

type Severidade = 'critico' | 'cuidado' | 'informativo';

interface Alerta {
  id: number;
  tipo: string;
  severidade: Severidade;
  titulo: string;
  descricao: string;
  lido: boolean;
  timestamp: string;
}

type Filtro = 'todos' | Severidade;

const SEVERIDADE_CONFIG: Record<Severidade, { label: string; cor: string; icone: keyof typeof Ionicons.glyphMap }> = {
  critico: { label: 'Crítico', cor: colors.danger, icone: 'warning' },
  cuidado: { label: 'Cuidado', cor: colors.cuidado, icone: 'warning' },
  informativo: { label: 'Informativo', cor: colors.informativo, icone: 'information-circle' },
};

const FILTROS: { chave: Filtro; label: string }[] = [
  { chave: 'todos', label: 'Todos' },
  { chave: 'critico', label: 'Crítico' },
  { chave: 'cuidado', label: 'Cuidado' },
  { chave: 'informativo', label: 'Informativo' },
];

function formatarData(timestamp: string) {
  const data = new Date(timestamp);
  const dataStr = data.toLocaleDateString('pt-BR');
  const horaStr = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${dataStr}, ${horaStr}`;
}

export default function AlertasScreen() {
  const [alertas, setAlertas] = useState<Alerta[]>(alertasMock as Alerta[]);
  const [filtro, setFiltro] = useState<Filtro>('todos');

  function marcarComoLido(id: number) {
    // TODO: quando a API estiver pronta, trocar por PATCH /alertas/{id}/lido
    setAlertas((prev) => prev.map((a) => (a.id === id ? { ...a, lido: true } : a)));
  }

  const alertasFiltrados = useMemo(
    () => (filtro === 'todos' ? alertas : alertas.filter((a) => a.severidade === filtro)),
    [alertas, filtro]
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image source={require('../../assets/images/logo-ecovision.png')} style={styles.logo} />
        <Text style={styles.headerTitulo}>Seus Alertas</Text>
        <View style={{ width: 32 }} />
      </View>

      <View style={styles.filtrosContainer}>
        {FILTROS.map((f) => {
          const selecionado = filtro === f.chave;
          const cor = f.chave === 'todos' ? colors.oliveGreen : SEVERIDADE_CONFIG[f.chave as Severidade].cor;
          return (
            <Pressable
              key={f.chave}
              onPress={() => setFiltro(f.chave)}
              style={[
                styles.filtroChip,
                selecionado && f.chave === 'todos' && { backgroundColor: colors.oliveGreen, borderColor: colors.oliveGreen },
                selecionado && f.chave !== 'todos' && { borderColor: cor },
              ]}
            >
              {f.chave !== 'todos' && <View style={[styles.filtroDot, { backgroundColor: cor }]} />}
              <Text
                style={[
                  styles.filtroTexto,
                  selecionado && f.chave === 'todos' && { color: colors.white },
                  selecionado && f.chave !== 'todos' && { color: cor },
                ]}
              >
                {f.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <FlatList
        style={styles.lista}
        contentContainerStyle={styles.listaConteudo}
        data={alertasFiltrados}
        keyExtractor={(item) => String(item.id)}
        ListEmptyComponent={<Text style={styles.vazioTexto}>Nenhum alerta nesta categoria.</Text>}
        renderItem={({ item }) => {
          const config = SEVERIDADE_CONFIG[item.severidade];
          return (
            <View style={styles.card}>
              <View style={[styles.faixa, { backgroundColor: config.cor }]}>
                <View style={styles.faixaEsquerda}>
                  <Ionicons name={config.icone} size={16} color={colors.white} />
                  <Text style={styles.faixaTexto}>{config.label}</Text>
                </View>
                {!item.lido && (
                  <View style={styles.novoBadge}>
                    <Text style={styles.novoTexto}>novo</Text>
                  </View>
                )}
              </View>

              <View style={styles.corpo}>
                <Text style={styles.titulo}>{item.titulo}</Text>
                <Text style={[styles.descricao, { color: config.cor }]}>{item.descricao}</Text>
                <Text style={styles.data}>{formatarData(item.timestamp)}</Text>

                <Pressable
                  style={[styles.botao, item.lido && styles.botaoLido]}
                  onPress={() => marcarComoLido(item.id)}
                  disabled={item.lido}
                >
                  <Ionicons name="checkmark" size={16} color={item.lido ? colors.textMuted : colors.oliveGreen} />
                  <Text style={[styles.botaoTexto, item.lido && styles.botaoTextoLido]}>
                    {item.lido ? 'Lido' : 'Marcar como lido'}
                  </Text>
                </Pressable>
              </View>
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  header: {
    backgroundColor: colors.darkGreen,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 50,
    paddingBottom: 16,
  },
  logo: { width: 32, height: 32, resizeMode: 'contain' },
  headerTitulo: { color: colors.white, fontSize: 18, fontWeight: '700' },
  filtrosContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 4,
  },
  filtroChip: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#DADAD2',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: colors.white,
  },
  filtroDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  filtroTexto: { fontSize: 13, fontWeight: '600', color: colors.textDark },
  lista: { flex: 1 },
  listaConteudo: { padding: 12, paddingBottom: 24 },
  vazioTexto: { textAlign: 'center', color: colors.textMuted, marginTop: 32, fontSize: 14 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    marginBottom: 14,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  faixa: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  faixaEsquerda: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  faixaTexto: { color: colors.white, fontWeight: '700', fontSize: 13 },
  novoBadge: { backgroundColor: colors.novoBadgeBg, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  novoTexto: { color: colors.white, fontSize: 11, fontWeight: '700' },
  corpo: { padding: 14 },
  titulo: { fontSize: 15, fontWeight: '700', color: colors.textDark, marginBottom: 4 },
  descricao: { fontSize: 13, lineHeight: 18, marginBottom: 8 },
  data: { fontSize: 11, color: colors.textMuted, marginBottom: 12 },
  botao: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1.5,
    borderColor: colors.oliveGreen,
    borderRadius: 24,
    paddingVertical: 10,
  },
  botaoLido: { borderColor: '#DADAD2', backgroundColor: '#F2F2ED' },
  botaoTexto: { color: colors.oliveGreen, fontWeight: '700', fontSize: 13 },
  botaoTextoLido: { color: colors.textMuted },
});