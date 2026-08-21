/**
 * app/src/screens/HistoricoScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Histórico de leituras ambientais. Versão inicial em lista simples,
 * com dados mockados (src/mocks/leituras.json). Gráfico via
 * DiagnosticoChart será integrado depois.
 */

import React from "react";
import { View, Text, FlatList, StyleSheet } from "react-native";
import leiturasMock from "../mocks/leituras.json";

type LeituraAmbiental = {
  id: number;
  dispositivo_id: number;
  temperatura: number;
  umidade_ar: number;
  umidade_solo: number;
  timestamp: string;
};

export default function HistoricoScreen() {
  const leituras: LeituraAmbiental[] = leiturasMock;

  return (
    <FlatList
      style={styles.lista}
      data={leituras}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <Text style={styles.data}>
            {new Date(item.timestamp).toLocaleString("pt-BR")}
          </Text>
          <Text>Temperatura: {item.temperatura}°C</Text>
          <Text>Umidade do ar: {item.umidade_ar}%</Text>
          <Text>Umidade do solo: {item.umidade_solo}%</Text>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  lista: { flex: 1, padding: 16 },
  card: { backgroundColor: "#F0F7F0", borderRadius: 8, padding: 12, marginBottom: 12 },
  data: { fontWeight: "bold", marginBottom: 4 },
});