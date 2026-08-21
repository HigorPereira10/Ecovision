import React, { useState } from "react";
import { View, Text, FlatList, StyleSheet, Pressable } from "react-native";
import alertasMock from "../mocks/alertas.json";

type Severidade = "baixa" | "media" | "alta";

type Alerta = {
  id: number;
  tipo: string;
  severidade: Severidade;
  lido: boolean;
  timestamp: string;
};

const CORES_SEVERIDADE: Record<Severidade, string> = {
  baixa: "#4CAF50",
  media: "#FF9800",
  alta: "#E53935",
};

function tituloDoAlerta(tipo: string) {
  const mapa: Record<string, string> = {
    míldio: "Míldio detectado",
    praga: "Possível praga detectada",
    temperatura: "Alerta de temperatura",
    umidade: "Alerta de umidade",
  };
  return mapa[tipo] ?? `Alerta: ${tipo}`;
}

export default function AlertasScreen() {
  const [alertas, setAlertas] = useState<Alerta[]>(alertasMock as Alerta[]);

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
          <View style={styles.cabecalho}>
            <Text style={styles.titulo}>{tituloDoAlerta(item.tipo)}</Text>
            <View
              style={[
                styles.badge,
                { backgroundColor: CORES_SEVERIDADE[item.severidade] },
              ]}
            >
              <Text style={styles.badgeTexto}>{item.severidade}</Text>
            </View>
          </View>
          <Text style={styles.data}>
            {new Date(item.timestamp).toLocaleString("pt-BR")}
          </Text>
        </Pressable>
      )}
    />
  );
}

const styles = StyleSheet.create({
  lista: { flex: 1, padding: 16 },
  card: { backgroundColor: "#FFF3F3", borderRadius: 8, padding: 12, marginBottom: 12 },
  cardLido: { backgroundColor: "#F0F0F0", opacity: 0.6 },
  cabecalho: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  titulo: { fontWeight: "bold", fontSize: 16, flexShrink: 1 },
  badge: { borderRadius: 12, paddingHorizontal: 8, paddingVertical: 2, marginLeft: 8 },
  badgeTexto: { color: "#fff", fontSize: 12, fontWeight: "bold" },
  data: { marginTop: 8, fontSize: 12, color: "#666" },
});