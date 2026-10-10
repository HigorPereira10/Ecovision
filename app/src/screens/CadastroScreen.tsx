/**
 * app/src/screens/CadastroScreen.tsx
 *
 * Tela de cadastro do produtor. Mesmo visual da LoginScreen
 * (topo verde com gradiente + card creme).
 *
 * Campos: nome completo, e-mail, senha, confirmar senha.
 * Consome registrar() de app/src/services/auth.ts, que chama
 * POST /auth/register no FastAPI.
 *
 * A data de nascimento foi removida: nenhuma funcionalidade do sistema
 * usa a idade do produtor, e a LGPD manda coletar apenas o
 * indispensavel para a finalidade declarada (principio da
 * necessidade). Guardar essa data criaria obrigacao sem entregar nada.
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
  Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation } from "@react-navigation/native";
import { registrar } from "../services/auth";
import { colors } from "../theme/colors";

// ---------- Regras de validação ----------

const REGRAS_SENHA = [
  { id: "tamanho", texto: "Mínimo de 8 caracteres", teste: (s: string) => s.length >= 8 },
  { id: "maiuscula", texto: "Uma letra maiúscula", teste: (s: string) => /[A-Z]/.test(s) },
  { id: "minuscula", texto: "Uma letra minúscula", teste: (s: string) => /[a-z]/.test(s) },
  { id: "numero", texto: "Um número", teste: (s: string) => /\d/.test(s) },
  {
    id: "simbolo",
    texto: "Um símbolo (!@#$%...)",
    teste: (s: string) => /[^A-Za-z0-9]/.test(s),
  },
];

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Erros = Partial<Record<"nome" | "email" | "senha" | "confirmar", string>>;

function validar(
  nome: string,
  email: string,
  senha: string,
  confirmar: string
): Erros {
  const erros: Erros = {};

  if (nome.trim().split(/\s+/).filter(Boolean).length < 2) {
    erros.nome = "Informe nome e sobrenome.";
  }

  if (!EMAIL_REGEX.test(email.trim())) {
    erros.email = "Informe um e-mail válido.";
  }

  if (!REGRAS_SENHA.every((r) => r.teste(senha))) {
    erros.senha = "A senha não atende a todos os requisitos.";
  }

  if (confirmar !== senha || confirmar.length === 0) {
    erros.confirmar = "As senhas não coincidem.";
  }

  return erros;
}

// ---------- Tela ----------

export default function CadastroScreen() {
  const navigation = useNavigation<any>();

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [confirmarVisivel, setConfirmarVisivel] = useState(false);

  const [erros, setErros] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function handleCadastro() {
    setErroGeral(null);
    const novosErros = validar(nome, email, senha, confirmar);
    setErros(novosErros);
    if (Object.keys(novosErros).length > 0) return;

    setCarregando(true);
    try {
      await registrar({
        nome: nome.trim(),
        email: email.trim().toLowerCase(),
        senha,
      });

      Alert.alert("Conta criada!", "Agora é só entrar com seu e-mail e senha.", [
        { text: "OK", onPress: () => navigation.goBack() },
      ]);
    } catch (e) {
      setErroGeral(e instanceof Error ? e.message : "Erro ao criar conta.");
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

          <Text style={styles.headerTitulo}>Criar conta</Text>

          <Image
            source={require("../../assets/images/logo-ecovision.png")}
            style={styles.logo}
            resizeMode="contain"
          />

          <View style={styles.divisor} />
        </LinearGradient>

        {/* Formulário */}
        <View style={styles.formulario}>
          {/* Nome */}
          <Text style={styles.label}>Nome completo</Text>
          <TextInput
            style={[styles.input, erros.nome && styles.inputErro]}
            placeholder="Maria da Silva"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="words"
            value={nome}
            onChangeText={setNome}
          />
          {erros.nome && <Text style={styles.erroCampo}>{erros.nome}</Text>}

          {/* E-mail */}
          <Text style={[styles.label, styles.labelEspaco]}>E-mail</Text>
          <TextInput
            style={[styles.input, erros.email && styles.inputErro]}
            placeholder="produtor@ecovision.app"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
          {erros.email && <Text style={styles.erroCampo}>{erros.email}</Text>}

          {/* Senha */}
          <Text style={[styles.label, styles.labelEspaco]}>Senha</Text>
          <View
            style={[styles.inputSenhaContainer, erros.senha && styles.inputErro]}
          >
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
          {erros.senha && <Text style={styles.erroCampo}>{erros.senha}</Text>}

          {/* Checklist de requisitos (atualiza enquanto digita) */}
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
                    style={[
                      styles.requisitoTexto,
                      ok && { color: colors.oliveGreen },
                    ]}
                  >
                    {r.texto}
                  </Text>
                </View>
              );
            })}
          </View>

          {/* Confirmar senha */}
          <Text style={[styles.label, styles.labelEspaco]}>Confirmar senha</Text>
          <View
            style={[
              styles.inputSenhaContainer,
              erros.confirmar && styles.inputErro,
            ]}
          >
            <TextInput
              style={styles.inputSenha}
              placeholder="••••••••"
              placeholderTextColor={colors.textMuted}
              secureTextEntry={!confirmarVisivel}
              autoCapitalize="none"
              value={confirmar}
              onChangeText={setConfirmar}
            />
            <TouchableOpacity
              onPress={() => setConfirmarVisivel((v) => !v)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Ionicons
                name={confirmarVisivel ? "eye-off" : "eye"}
                size={20}
                color={colors.textMuted}
              />
            </TouchableOpacity>
          </View>
          {erros.confirmar && (
            <Text style={styles.erroCampo}>{erros.confirmar}</Text>
          )}

          {erroGeral && <Text style={styles.erro}>{erroGeral}</Text>}

          <TouchableOpacity
            style={styles.botao}
            onPress={handleCadastro}
            disabled={carregando}
          >
            {carregando ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.botaoTexto}>Criar conta</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkLogin}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.linkLoginTexto}>
              Já tem conta? <Text style={styles.linkLoginDestaque}>Entrar</Text>
            </Text>
          </TouchableOpacity>
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
  erroCampo: {
    color: colors.danger,
    fontSize: 12,
    marginTop: 6,
  },
  requisitos: { marginTop: 12, gap: 4 },
  requisitoLinha: { flexDirection: "row", alignItems: "center", gap: 6 },
  requisitoTexto: { fontSize: 12, color: colors.textMuted },
  erro: {
    color: colors.danger,
    textAlign: "center",
    marginTop: 16,
  },
  botao: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 28,
  },
  botaoTexto: { color: colors.white, fontSize: 16, fontWeight: "700" },
  linkLogin: { alignItems: "center", marginTop: 20 },
  linkLoginTexto: { color: colors.textDark, fontSize: 14 },
  linkLoginDestaque: {
    color: colors.oliveGreen,
    fontWeight: "700",
    textDecorationLine: "underline",
  },
});