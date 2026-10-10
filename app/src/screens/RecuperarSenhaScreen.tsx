/**
 * app/src/screens/RecuperarSenhaScreen.tsx
 *
 * Redefinição de senha em dois passos, na mesma tela:
 *   1. o produtor informa o e-mail e recebe um código de 6 dígitos;
 *   2. digita o código e a senha nova.
 *
 * Os dois passos ficam juntos de propósito: o código chega por e-mail,
 * então o produtor volta ao app em seguida, e mandá-lo navegar de novo
 * até outra tela só criaria uma chance a mais de se perder no caminho.
 *
 * Esta tela era MOCKADA: dizia "confira seu e-mail" sem que e-mail
 * nenhum saísse. Agora consome POST /auth/forgot-password e
 * POST /auth/reset-password de verdade.
 *
 * A mensagem do primeiro passo é a mesma exista ou não conta com aquele
 * endereço, e a API responde igual nos dois casos: diferenciar
 * permitiria descobrir quais e-mails estão cadastrados testando
 * endereços.
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
import { solicitarRecuperacaoSenha, redefinirSenha } from "../services/auth";
import { colors } from "../theme/colors";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Mesmas regras que o servidor exige em POST /auth/reset-password. A
 * validação aqui é conveniência: quem chamar a API direto passa por
 * cima dela, e por isso ela existe também no backend. */
const REGRAS_SENHA = [
  { id: "tamanho", texto: "Mínimo de 8 caracteres", teste: (s: string) => s.length >= 8 },
  { id: "maiuscula", texto: "Uma letra maiúscula", teste: (s: string) => /[A-Z]/.test(s) },
  { id: "minuscula", texto: "Uma letra minúscula", teste: (s: string) => /[a-z]/.test(s) },
  { id: "numero", texto: "Um número", teste: (s: string) => /\d/.test(s) },
  { id: "simbolo", texto: "Um símbolo (!@#$%...)", teste: (s: string) => /[^A-Za-z0-9]/.test(s) },
];

type Passo = "email" | "codigo" | "pronto";

export default function RecuperarSenhaScreen() {
  const navigation = useNavigation<any>();

  const [passo, setPasso] = useState<Passo>("email");
  const [email, setEmail] = useState("");
  const [codigo, setCodigo] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  const senhaValida = REGRAS_SENHA.every((r) => r.teste(senha));
  const podeRedefinir = codigo.length === 6 && senhaValida;

  async function handlePedirCodigo() {
    setErro(null);
    if (!EMAIL_REGEX.test(email.trim())) {
      setErro("Informe um e-mail válido.");
      return;
    }

    setCarregando(true);
    try {
      await solicitarRecuperacaoSenha(email);
      setPasso("codigo");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível enviar o código.");
    } finally {
      setCarregando(false);
    }
  }

  async function handleRedefinir() {
    setErro(null);
    setCarregando(true);
    try {
      await redefinirSenha(email, codigo, senha);
      setPasso("pronto");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível alterar a senha.");
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
        <LinearGradient colors={[colors.darkGreen, colors.green]} style={styles.topo}>
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

        <View style={styles.formulario}>
          {passo === "pronto" ? (
            <View style={styles.sucesso}>
              <Ionicons name="checkmark-circle" size={48} color={colors.oliveGreen} />
              <Text style={styles.sucessoTitulo}>Senha alterada</Text>
              <Text style={styles.sucessoTexto}>
                Agora é só entrar com a nova senha.
              </Text>

              <TouchableOpacity
                style={styles.botao}
                onPress={() => navigation.navigate("Login")}
              >
                <Text style={styles.botaoTexto}>Ir para o login</Text>
              </TouchableOpacity>
            </View>
          ) : passo === "codigo" ? (
            <>
              <Text style={styles.descricao}>
                Se {email.trim()} estiver cadastrado, um código de 6 dígitos foi
                enviado para lá. Verifique também a caixa de spam.
              </Text>

              <Text style={styles.label}>Código</Text>
              <TextInput
                style={[styles.inputCodigo, erro && styles.inputErro]}
                placeholder="000000"
                placeholderTextColor={colors.textMuted}
                keyboardType="number-pad"
                maxLength={6}
                value={codigo}
                onChangeText={(t) => setCodigo(t.replace(/\D/g, "").slice(0, 6))}
              />

              <Text style={[styles.label, styles.labelEspaco]}>Nova senha</Text>
              <View style={[styles.inputSenhaContainer, erro && styles.inputErro]}>
                <TextInput
                  style={styles.inputSenha}
                  placeholder="••••••••"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!senhaVisivel}
                  autoCapitalize="none"
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

              <View style={styles.requisitos}>
                {REGRAS_SENHA.map((r) => {
                  const ok = r.teste(senha);
                  return (
                    <View key={r.id} style={styles.requisitoLinha}>
                      <Ionicons
                        name={ok ? "checkmark-circle" : "ellipse-outline"}
                        size={16}
                        color={ok ? colors.oliveGreen : colors.textMuted}
                      />
                      <Text
                        style={[styles.requisitoTexto, ok && { color: colors.oliveGreen }]}
                      >
                        {r.texto}
                      </Text>
                    </View>
                  );
                })}
              </View>

              {erro && <Text style={styles.erro}>{erro}</Text>}

              <TouchableOpacity
                style={[styles.botao, !podeRedefinir && styles.botaoDesabilitado]}
                onPress={handleRedefinir}
                disabled={carregando}
              >
                {carregando ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.botaoTexto}>Alterar senha</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.linkSecundario}
                onPress={() => {
                  setPasso("email");
                  setCodigo("");
                  setErro(null);
                }}
              >
                <Text style={styles.linkSecundarioTexto}>Usar outro e-mail</Text>
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={styles.descricao}>
                Informe o e-mail da sua conta. Enviaremos um código para você criar
                uma nova senha.
              </Text>

              <Text style={styles.label}>E-mail</Text>
              <TextInput
                style={[styles.input, erro && styles.inputErro]}
                placeholder="produtor@ecovision.app"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                value={email}
                onChangeText={setEmail}
              />

              {erro && <Text style={styles.erro}>{erro}</Text>}

              <TouchableOpacity
                style={styles.botao}
                onPress={handlePedirCodigo}
                disabled={carregando}
              >
                {carregando ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.botaoTexto}>Enviar código</Text>
                )}
              </TouchableOpacity>
            </>
          )}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const sombra = {
  shadowColor: "#000",
  shadowOpacity: 0.05,
  shadowRadius: 4,
  shadowOffset: { width: 0, height: 2 },
  elevation: 1,
} as const;

const styles = StyleSheet.create({
  scrollContent: { flexGrow: 1 },
  topo: {
    alignItems: "center",
    paddingTop: 50,
    paddingBottom: 32,
    paddingHorizontal: 24,
  },
  botaoVoltar: { position: "absolute", left: 20, top: 50 },
  headerTitulo: {
    color: colors.white,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 24,
  },
  logo: { width: 120, height: 120, marginBottom: 16 },
  divisor: { width: 80, height: 2, backgroundColor: colors.white, opacity: 0.6 },
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
    fontSize: 14,
    color: colors.textMuted,
    lineHeight: 20,
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: colors.textDark,
    marginBottom: 8,
  },
  labelEspaco: { marginTop: 20 },
  input: {
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: colors.textDark,
    borderWidth: 1,
    borderColor: "transparent",
    ...sombra,
  },
  inputCodigo: {
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 26,
    letterSpacing: 10,
    textAlign: "center",
    color: colors.textDark,
    borderWidth: 1,
    borderColor: "transparent",
    ...sombra,
  },
  inputSenhaContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: "transparent",
    ...sombra,
  },
  inputSenha: {
    flex: 1,
    paddingVertical: 14,
    fontSize: 15,
    color: colors.textDark,
  },
  inputErro: { borderColor: colors.danger },
  erro: { color: colors.danger, fontSize: 13, marginTop: 12, lineHeight: 18 },
  requisitos: { marginTop: 12, gap: 4 },
  requisitoLinha: { flexDirection: "row", alignItems: "center", gap: 6 },
  requisitoTexto: { fontSize: 12, color: colors.textMuted },
  botao: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 28,
  },
  botaoDesabilitado: { opacity: 0.5 },
  botaoTexto: { color: colors.white, fontSize: 16, fontWeight: "700" },
  linkSecundario: { alignItems: "center", marginTop: 16 },
  linkSecundarioTexto: { color: colors.oliveGreen, fontWeight: "600", fontSize: 14 },
  sucesso: { alignItems: "center", paddingTop: 12 },
  sucessoTitulo: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.textDark,
    marginTop: 16,
    marginBottom: 8,
  },
  sucessoTexto: {
    fontSize: 14,
    color: colors.textMuted,
    textAlign: "center",
    lineHeight: 20,
  },
});
