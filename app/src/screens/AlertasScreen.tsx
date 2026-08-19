/**
 * app/src/screens/AlertasScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Lista os alertas do produtor autenticado. Por enquanto usa dados
 * mockados (src/mocks/alertas.json) até a API estar pronta.
 */

import React, { useState } from "react";
import { View, Text, FlatList, StyleSheet, Pressable } from "react-native";
import alertasMock from "../mocks/alertas.json";

type Alerta = {
  id: number;
  titulo: string;
  descricao: string;
  lido: boolean;
  data: string;
};

export default function AlertasScreen() {
  const [alertas, setAlertas] = useState<Alerta[]>(alertasMock);

  function marcarComoLido(id: number) {
    // TODO: quando a API estiver pronta, trocar por PATCH /alertas/{id}/lido
    setAlertas((prev) =>
      prev.map((a) => (a.id === id ? { ...a, lido: true } : a))
    );
  }

  return (
    <FlatList
      style={styles.lista}
      data={alertas}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <Pressable
          style={[styles.card, item.lido && styles.cardLido]}
          onPress={() => marcarComoLido(item.id)}
        >
          <Text style={styles.titulo}>{item.titulo}</Text>
          <Text style={styles.descricao}>{item.descricao}</Text>
          <Text style={styles.data}>{new Date(item.data).toLocaleString("pt-BR")}</Text>
        </Pressable>
      )}
    />
  );
}

const styles = StyleSheet.create({
  lista: { flex: 1, padding: 16 },
  card: {
    backgroundColor: "#FFF3F3",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  cardLido: {
    backgroundColor: "#F0F0F0",
    opacity: 0.6,
  },
  titulo: { fontWeight: "bold", fontSize: 16 },
  descricao: { marginTop: 4 },
  data: { marginTop: 8, fontSize: 12, color: "#666" },
});