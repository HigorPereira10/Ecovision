/**
 * app/src/screens/RecuperarSenhaScreen.tsx
 *
 * Tela de recuperação de senha, acessada pelo link "Esqueci a senha?"
 * da LoginScreen. O usuário informa o e-mail e recebe instruções para
 * redefinir a senha.
 *
 * Consome solicitarRecuperacaoSenha() de app/src/services/auth.ts
 * (hoje mockada, futuramente POST /auth/forgot-password no FastAPI).
 *
 * A mensagem de sucesso é a mesma exista ou não conta com o e-mail
 * informado, para não revelar quais e-mails estão cadastrados.
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
import { useNavigation } from "@react-navigation/native";
import { solicitarRecuperacaoSenha } from "../services/auth";
import { colors } from "../theme/colors";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RecuperarSenhaScreen() {
  const navigation = useNavigation<any>();

  const [email, setEmail] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  async function handleEnviar() {
    setErro(null);

    if (!EMAIL_REGEX.test(email.trim())) {
      setErro("Informe um e-mail válido.");
      return;
    }

    setCarregando(true);
    try {
      await solicitarRecuperacaoSenha(email.trim().toLowerCase());
      setEnviado(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao enviar instruções.");
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
        {/* Topo verde */}
        <LinearGradient
          colors={[colors.darkGreen, colors.green]}
          style={styles.topo}
        >
          <TouchableOpacity
            style={styles.botaoVoltar}
            onPress={() => navigation.goBack()}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="arrow-back" size={22} color={colors.white} />
          </TouchableOpacity>

          <Text style={styles.headerTitulo}>Recuperar senha</Text>

          <Image
            source={require("../../assets/images/logo-ecovision.png")}
            style={styles.logo}
            resizeMode="contain"
          />

          <View style={styles.divisor} />
        </LinearGradient>

        {/* Conteúdo */}
        <View style={styles.formulario}>
          {enviado ? (
            <View style={styles.sucesso}>
              <Ionicons
                name="mail-outline"
                size={48}
                color={colors.oliveGreen}
              />
              <Text style={styles.sucessoTitulo}>Confira seu e-mail</Text>
              <Text style={styles.sucessoTexto}>
                Se {email.trim()} estiver cadastrado, você vai receber as
                instruções para criar uma nova senha. Verifique também a caixa
                de spam.
              </Text>

              <TouchableOpacity
                style={styles.botao}
                onPress={() => navigation.goBack()}
              >
                <Text style={styles.botaoTexto}>Voltar ao login</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.linkSecundario}
                onPress={() => setEnviado(false)}
              >
                <Text style={styles.linkSecundarioTexto}>
                  Usar outro e-mail
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <Text style={styles.descricao}>
                Informe o e-mail da sua conta. Enviaremos as instruções para
                você criar uma nova senha.
              </Text>

              <Text style={styles.label}>E-mail</Text>
              <TextInput
                style={[styles.input, erro && styles.inputErro]}
                placeholder="produtor@ecovision.app"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                keyboardType="email-address"
                value={email}
                onChangeText={setEmail}
              />

              {erro && <Text style={styles.erro}>{erro}</Text>}

              <TouchableOpacity
                style={styles.botao}
                onPress={handleEnviar}
                disabled={carregando}
              >
                {carregando ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.botaoTexto}>Enviar instruções</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.linkSecundario}
                onPress={() => navigation.goBack()}
              >
                <Text style={styles.linkSecundarioTexto}>Voltar ao login</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  scrollContent: { flexGrow: 1 },
  topo: {
    alignItems: "center",
    paddingTop: 50,
    paddingBottom: 32,
    paddingHorizontal: 24,
  },
  botaoVoltar: {
    position: "absolute",
    left: 20,
    top: 50,
  },
  headerTitulo: {
    color: colors.white,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 24,
  },
  logo: { width: 120, height: 120, marginBottom: 16 },
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
  descricao: {
    color: colors.textDark,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 24,
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
    borderWidth: 1,
    borderColor: "transparent",
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  inputErro: { borderColor: colors.danger },
  erro: {
    color: colors.danger,
    fontSize: 13,
    marginTop: 8,
  },
  botao: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 28,
    alignSelf: "stretch",
  },
  botaoTexto: { color: colors.white, fontSize: 16, fontWeight: "700" },
  linkSecundario: { alignItems: "center", marginTop: 20 },
  linkSecundarioTexto: {
    color: colors.oliveGreen,
    fontSize: 14,
    fontWeight: "600",
    textDecorationLine: "underline",
  },
  sucesso: { alignItems: "center", paddingTop: 8 },
  sucessoTitulo: {
    color: colors.textDark,
    fontSize: 18,
    fontWeight: "700",
    marginTop: 16,
    marginBottom: 8,
  },
  sucessoTexto: {
    color: colors.textDark,
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
  },
});
