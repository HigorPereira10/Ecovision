/**
 * app/src/screens/DiagnosticoScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Exibe o diagnóstico mais recente, incluindo a foto da folha. A URL
 * da imagem vem PRONTA da API (Blueprint Seção 4.2, passo 5) — esta
 * tela nunca busca a imagem diretamente no Supabase Storage.
 *
 * Versão atual usa dados mockados (src/mocks/diagnosticos.json) até
 * o endpoint da API estar definido/pronto.
 */

import React from "react";
import { View, Image, Text, StyleSheet, ScrollView } from "react-native";
import diagnosticosMock from "../mocks/diagnosticos.json";

export default function DiagnosticoScreen() {
  // Por enquanto, sempre mostra o mais recente (primeiro do mock)
  const diagnostico = diagnosticosMock[0];

  if (!diagnostico) {
    return (
      <View style={styles.container}>
        <Text>Nenhum diagnóstico disponível ainda.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Image source={{ uri: diagnostico.imagem_url }} style={styles.imagem} />

      <Text style={styles.resultado}>{diagnostico.resultado}</Text>
      <Text style={styles.confianca}>
        Confiança: {Math.round(diagnostico.confianca * 100)}%
      </Text>

      <Text style={styles.label}>Recomendação:</Text>
      <Text style={styles.recomendacao}>{diagnostico.recomendacao}</Text>

      <Text style={styles.data}>
        {new Date(diagnostico.data).toLocaleString("pt-BR")}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  imagem: {
    width: "100%",
    height: 220,
    borderRadius: 8,
    marginBottom: 16,
    backgroundColor: "#eee",
  },
  resultado: { fontSize: 20, fontWeight: "bold" },
  confianca: { color: "#666", marginTop: 4, marginBottom: 16 },
  label: { fontWeight: "bold", marginTop: 8 },
  recomendacao: { marginTop: 4 },
  data: { marginTop: 16, fontSize: 12, color: "#999" },
});