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

type Leitura = {
  data: string;
  temperatura: number;
  umidade: number;
};

export default function HistoricoScreen() {
  const leituras: Leitura[] = leiturasMock;

  return (
    <FlatList
      style={styles.lista}
      data={leituras}
      keyExtractor={(item) => item.data}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <Text style={styles.data}>{item.data}</Text>
          <Text>Temperatura: {item.temperatura}°C</Text>
          <Text>Umidade: {item.umidade}%</Text>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  lista: { flex: 1, padding: 16 },
  card: {
    backgroundColor: "#F0F7F0",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  data: { fontWeight: "bold", marginBottom: 4 },
});