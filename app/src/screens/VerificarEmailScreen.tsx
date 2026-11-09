/**
 * Confirmação do cadastro pelo código de 6 dígitos enviado por e-mail. O
 * e-mail chega por parâmetro de rota, vindo do cadastro.
 *
 * O botão de reenvio fica bloqueado por SEGUNDOS_PARA_REENVIO, com
 * contagem regressiva, porque a API ignora pedidos dentro desse intervalo
 * e responde da mesma forma em qualquer caso.
 */

import React, { useEffect, useState } from "react";
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
import { useNavigation, useRoute } from "@react-navigation/native";
import { reenviarCodigo, verificarEmail } from "../services/auth";
import { colors } from "../theme/colors";

/** Deve ser maior ou igual a _INTERVALO_REENVIO em
 * cloud/app/api/routes/auth.py; a folga de 5 segundos cobre diferenças de
 * relógio. */
const SEGUNDOS_PARA_REENVIO = 65;

/** Mantém só dígitos e corta em 6: o código é numérico, e deixar o
 * produtor digitar letras só produziria um erro depois. */
function mascararCodigo(texto: string): string {
  return texto.replace(/\D/g, "").slice(0, 6);
}

export default function VerificarEmailScreen() {
  const navigation = useNavigation<any>();
  const rota = useRoute<any>();
  const email: string = rota.params?.email ?? "";

  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [confirmado, setConfirmado] = useState(false);
  const [segundosRestantes, setSegundosRestantes] = useState(SEGUNDOS_PARA_REENVIO);
  const [avisoReenvio, setAvisoReenvio] = useState<string | null>(null);
  const [reenviando, setReenviando] = useState(false);

  const codigoCompleto = codigo.length === 6;
  const podeReenviar = segundosRestantes === 0 && !reenviando;

  // Um único intervalo de 1 s, criado na montagem e desfeito na
  // desmontagem; o contador para em zero.
  useEffect(() => {
    const timer = setInterval(() => {
      setSegundosRestantes((anterior) => (anterior <= 1 ? 0 : anterior - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  async function handleReenviar() {
    setReenviando(true);
    setErro(null);
    try {
      await reenviarCodigo(email);
      // A API responde igual em todos os casos, então a mensagem fala
      // do que foi pedido, não do que aconteceu. Prometer "enviamos"
      // seria afirmar algo que esta tela não tem como saber.
      setAvisoReenvio("Pedido enviado. Se houver cadastro pendente, o código chega em instantes.");
      setSegundosRestantes(SEGUNDOS_PARA_REENVIO);
      setCodigo("");
    } catch (e) {
      setAvisoReenvio(null);
      setErro(e instanceof Error ? e.message : "Não foi possível pedir um código novo.");
    } finally {
      setReenviando(false);
    }
  }

  async function handleVerificar() {
    setErro(null);
    if (!codigoCompleto) {
      setErro("Digite os 6 dígitos do código.");
      return;
    }

    setCarregando(true);
    try {
      await verificarEmail(email, codigo);
      setConfirmado(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível confirmar o código.");
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

          <Text style={styles.headerTitulo}>Confirmar e-mail</Text>

          <Image
            source={require("../../assets/images/logo-ecovision.png")}
            style={styles.logo}
            resizeMode="contain"
          />

          <View style={styles.divisor} />
        </LinearGradient>

        <View style={styles.formulario}>
          {confirmado ? (
            <View style={styles.sucesso}>
              <Ionicons name="checkmark-circle" size={48} color={colors.oliveGreen} />
              <Text style={styles.sucessoTitulo}>E-mail confirmado</Text>
              <Text style={styles.sucessoTexto}>
                Sua conta está ativa. Agora é só entrar com o e-mail e a senha que
                você cadastrou.
              </Text>

              <TouchableOpacity
                style={styles.botao}
                onPress={() => navigation.navigate("Login")}
              >
                <Text style={styles.botaoTexto}>Ir para o login</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <Text style={styles.descricao}>
                Enviamos um código de 6 dígitos para{"\n"}
                <Text style={styles.emailDestaque}>{email}</Text>
              </Text>

              <Text style={styles.label}>Código</Text>
              <TextInput
                style={[styles.input, erro && styles.inputErro]}
                placeholder="000000"
                placeholderTextColor={colors.textMuted}
                keyboardType="number-pad"
                maxLength={6}
                value={codigo}
                onChangeText={(t) => setCodigo(mascararCodigo(t))}
              />

              {erro && <Text style={styles.erro}>{erro}</Text>}

              <View style={styles.dica}>
                <Ionicons
                  name="information-circle-outline"
                  size={16}
                  color={colors.textMuted}
                />
                <Text style={styles.dicaTexto}>
                  O código vale por 15 minutos. Se não encontrar o e-mail, veja
                  também a caixa de spam.
                </Text>
              </View>

              <TouchableOpacity
                style={[styles.botao, !codigoCompleto && styles.botaoDesabilitado]}
                onPress={handleVerificar}
                disabled={carregando}
              >
                {carregando ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.botaoTexto}>Confirmar</Text>
                )}
              </TouchableOpacity>

              {avisoReenvio && <Text style={styles.avisoReenvio}>{avisoReenvio}</Text>}

              <TouchableOpacity
                style={styles.linkReenviar}
                onPress={handleReenviar}
                disabled={!podeReenviar}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              >
                {reenviando ? (
                  <ActivityIndicator size="small" color={colors.oliveGreen} />
                ) : (
                  <Text
                    style={[
                      styles.linkReenviarTexto,
                      !podeReenviar && styles.linkReenviarDesabilitado,
                    ]}
                  >
                    {podeReenviar
                      ? "Não recebi o código. Enviar outro"
                      : `Pedir outro código em ${segundosRestantes}s`}
                  </Text>
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
    lineHeight: 21,
    marginBottom: 24,
  },
  emailDestaque: { color: colors.textDark, fontWeight: "700" },
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
    fontSize: 26,
    letterSpacing: 10,
    textAlign: "center",
    color: colors.textDark,
    borderWidth: 1,
    borderColor: "transparent",
    ...sombra,
  },
  inputErro: { borderColor: colors.danger },
  erro: { color: colors.danger, fontSize: 13, marginTop: 10, lineHeight: 18 },
  dica: { flexDirection: "row", gap: 8, marginTop: 16, paddingRight: 8 },
  dicaTexto: { flex: 1, fontSize: 12, color: colors.textMuted, lineHeight: 17 },
  botao: {
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 28,
  },
  botaoDesabilitado: { opacity: 0.5 },
  botaoTexto: { color: colors.white, fontSize: 16, fontWeight: "700" },
  avisoReenvio: {
    fontSize: 13,
    color: colors.oliveGreen,
    lineHeight: 18,
    marginTop: 16,
    textAlign: "center",
  },
  linkReenviar: { marginTop: 18, alignItems: "center", minHeight: 22 },
  linkReenviarTexto: { fontSize: 14, fontWeight: "600", color: colors.oliveGreen },
  // Cinza no estado travado, para o toque sem efeito nao parecer falha
  // do app: o texto ao lado ja diz quantos segundos faltam.
  linkReenviarDesabilitado: { color: colors.textMuted, fontWeight: "400" },
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
