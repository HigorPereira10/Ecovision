/**
 * app/src/screens/FinanceiroScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Tela financeira MOCK — sem integração de backend real (Blueprint v3.0).
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";

export default function FinanceiroScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.titulo}>Financeiro</Text>
      <Text style={styles.aviso}>
        Dados simulados — sem integração real com o backend por enquanto.
      </Text>

      <View style={styles.card}>
        <Text style={styles.label}>Custo estimado do mês</Text>
        <Text style={styles.valor}>R$ 1.240,00</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Economia com detecção precoce</Text>
        <Text style={styles.valor}>R$ 380,00</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, gap: 12 },
  titulo: { fontSize: 22, fontWeight: "bold" },
  aviso: { color: "#888", fontSize: 12, marginBottom: 12 },
  card: {
    backgroundColor: "#F5F5F5",
    borderRadius: 8,
    padding: 16,
  },
  label: { fontSize: 14, color: "#555" },
  valor: { fontSize: 20, fontWeight: "bold", marginTop: 4 },
});