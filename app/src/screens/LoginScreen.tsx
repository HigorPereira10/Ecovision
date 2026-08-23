/**
 * app/src/screens/LoginScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Tela de login do produtor, consumindo POST /auth/login
 * (cloud/app/api/routes/auth.py). Ao autenticar com sucesso, armazena
 * o JWT de acesso e o refresh token (ver app/src/services/auth.ts).
 *
 * Relação com o resto do sistema:
 * - Depende de app/src/services/auth.ts para a chamada HTTP.
 * - É a tela inicial do fluxo de navegação (app/src/navigation/AppNavigator.tsx).
 */

import React, { useState } from "react";
import { View, TextInput, Button, Text, StyleSheet, ActivityIndicator } from "react-native";
import { login } from "../services/auth";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
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
    <View style={styles.container}>
      <Text style={styles.titulo}>EcoVision</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />

      <TextInput
        style={styles.input}
        placeholder="Senha"
        secureTextEntry
        value={senha}
        onChangeText={setSenha}
      />

      {erro && <Text style={styles.erro}>{erro}</Text>}

      {carregando ? (
        <ActivityIndicator />
      ) : (
        <Button title="Entrar" onPress={handleLogin} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    gap: 12,
  },
  titulo: {
    fontSize: 28,
    fontWeight: "bold",
    textAlign: "center",
    marginBottom: 24,
  },
  input: {
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
    padding: 12,
  },
  erro: {
    color: "red",
    textAlign: "center",
  },
});