/**
 * Tela de boas-vindas, antes do login: logo, cartões com as
 * funcionalidades e botão "Entrar".
 */

import React from "react";
import {
  View,
  Text,
  Image,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { colors } from "../theme/colors";

type Props = {
  navigation: any; // troque pelo tipo do stack de auth quando integrar
};

const funcionalidades = [
  {
    icone: "wifi" as const,
    titulo: "IoT na estufa",
    descricao: "Sensores de temperatura, umidade do ar e do solo a cada ciclo.",
  },
  {
    icone: "camera" as const,
    titulo: "Captura automática",
    descricao: "Câmera registra as folhas sem inspeção manual.",
  },
  {
    icone: "leaf" as const,
    titulo: "IA de diagnóstico",
    descricao: "Classificação da doença com nível de confiança.",
  },
  {
    icone: "shield-checkmark" as const,
    titulo: "Alertas e manejo",
    descricao: "Recomendação prática por severidade do caso.",
  },
];

export default function WelcomeScreen({ navigation }: Props) {
  return (
    <LinearGradient
      colors={[colors.darkGreen, colors.green]}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Image
          source={require("../../assets/images/logo-ecovision.png")}
          style={styles.logo}
          resizeMode="contain"
        />

        <View style={styles.divisor} />

        <Text style={styles.titulo}>EcoVision</Text>
        <Text style={styles.subtitulo}>
          Monitoramento fitossanitário de estufas de tomate com IoT e visão
          computacional.
        </Text>

        <View style={styles.grid}>
          {funcionalidades.map((item) => (
            <View key={item.titulo} style={styles.card}>
              <Ionicons name={item.icone} size={20} color={colors.lightOlive} />
              <Text style={styles.cardTitulo}>{item.titulo}</Text>
              <Text style={styles.cardDescricao}>{item.descricao}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity
          style={styles.botaoEntrar}
          onPress={() => navigation.navigate("Login")}
        >
          <Text style={styles.botaoEntrarTexto}>Entrar</Text>
        </TouchableOpacity>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollContent: {
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 40,
  },
  logo: { width: 150, height: 150, marginBottom: 16 },
  divisor: {
    width: 100,
    height: 2,
    backgroundColor: colors.white,
    opacity: 0.6,
    marginBottom: 20,
  },
  titulo: {
    color: colors.white,
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 10,
  },
  subtitulo: {
    color: colors.textOnDark,
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 28,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    width: "100%",
    marginBottom: 32,
  },
  card: {
    width: "48%",
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 16,
    padding: 14,
    marginBottom: 14,
  },
  cardTitulo: {
    color: colors.white,
    fontSize: 14,
    fontWeight: "700",
    marginTop: 8,
    marginBottom: 4,
  },
  cardDescricao: {
    color: colors.textOnDark,
    fontSize: 12,
    lineHeight: 16,
  },
  botaoEntrar: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 16,
    width: "100%",
    alignItems: "center",
  },
  botaoEntrarTexto: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "700",
  },
});
