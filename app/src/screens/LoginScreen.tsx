/**
 * app/src/screens/LoginScreen.tsx
 *
 * Framework: Expo (React Native), decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Tela de login do produtor, consumindo POST /auth/login
 * (cloud/app/api/routes/auth.py). Ao autenticar com sucesso, armazena
 * o JWT de acesso e o refresh token (ver app/src/services/auth.ts).
 *
 * Relação com o resto do sistema:
 * - Depende de app/src/services/auth.ts para a chamada HTTP (hoje mockada).
 * - É acessada a partir de WelcomeScreen.tsx no stack de não-autenticado
 *   (app/src/navigation/AppNavigator.tsx).
 *
 * Visual: redesenhado para seguir o mockup (topo verde com logo + card
 * de formulário em creme). A LÓGICA de autenticação não foi alterada —
 * só a apresentação.
 *
 * Requer a dependência expo-linear-gradient:
 *   npx expo install expo-linear-gradient
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Image,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { login } from "../services/auth";
import { colors } from "../theme/colors";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function handleLogin() {
    setErro(null);
    setCarregando(true);
    try {
      await login(email, senha);
      // A navegação troca sozinha: o AppNavigator escuta isAuthenticated
      // via useEffect, então não precisa navegar manualmente aqui.
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao fazer login.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Topo verde com logo */}
        <LinearGradient
          colors={[colors.darkGreen, colors.green]}
          style={styles.topo}
        >
          <Text style={styles.headerTitulo}>Entrar</Text>

          <Image
            source={require("../../assets/images/logo-ecovision.png")}
            style={styles.logo}
            resizeMode="contain"
          />

          <View style={styles.divisor} />
        </LinearGradient>

        {/* Formulário */}
        <View style={styles.formulario}>
          <Text style={styles.label}>E-mail ou ID do Produtor</Text>
          <TextInput
            style={styles.input}
            placeholder="produtor@ecovision.app"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />

          <Text style={[styles.label, { marginTop: 20 }]}>Senha</Text>
          <View style={styles.inputSenhaContainer}>
            <TextInput
              style={styles.inputSenha}
              placeholder="••••••••"
              placeholderTextColor={colors.textMuted}
              secureTextEntry={!senhaVisivel}
              value={senha}
              onChangeText={setSenha}
            />
            <TouchableOpacity
              onPress={() => setSenhaVisivel((v) => !v)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Ionicons
                name={senhaVisivel ? "eye-off" : "eye"}
                size={20}
                color={colors.textMuted}
              />
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.linkEsqueci}>
            <Text style={styles.linkEsqueciTexto}>Esqueci a senha?</Text>
          </TouchableOpacity>

          {erro && <Text style={styles.erro}>{erro}</Text>}

          <TouchableOpacity
            style={styles.botaoEntrar}
            onPress={handleLogin}
            disabled={carregando}
          >
            {carregando ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.botaoEntrarTexto}>Entrar</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    flexGrow: 1,
  },
  topo: {
    alignItems: "center",
    paddingTop: 50,
    paddingBottom: 32,
    paddingHorizontal: 24,
  },
  headerTitulo: {
    color: colors.white,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 24,
  },
  logo: {
    width: 160,
    height: 160,
    marginBottom: 20,
  },
  divisor: {
    width: 80,
    height: 2,
    backgroundColor: colors.white,
    opacity: 0.6,
  },
  formulario: {
    flex: 1,
    backgroundColor: colors.cream,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    marginTop: -20,
    paddingHorizontal: 24,
    paddingTop: 32,
    paddingBottom: 40,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textDark,
    marginBottom: 8,
  },
  input: {
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: colors.textDark,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  inputSenhaContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: 16,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  inputSenha: {
    flex: 1,
    paddingVertical: 14,
    fontSize: 15,
    color: colors.textDark,
  },
  linkEsqueci: {
    alignSelf: "flex-end",
    marginTop: 10,
  },
  linkEsqueciTexto: {
    color: colors.oliveGreen,
    fontSize: 13,
    fontWeight: "600",
    textDecorationLine: "underline",
  },
  erro: {
    color: colors.danger,
    textAlign: "center",
    marginTop: 16,
  },
  botaoEntrar: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 28,
  },
  botaoEntrarTexto: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "700",
  },
});
