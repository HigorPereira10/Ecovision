/**
 * app/src/screens/VincularDispositivoScreen.tsx
 *
 * Tela de vínculo de um equipamento IoT à conta do produtor. Mesmo
 * visual da CadastroScreen (topo verde com gradiente + card creme).
 *
 * Por que esta tela existe: o cadastro é aberto, qualquer pessoa cria
 * conta. O que separa um produtor dos dados de outro é a posse física
 * do equipamento, provada ao digitar aqui o código que vem na etiqueta
 * dele. Antes disso, a conta não enxerga nada (ver app/api/escopo.py no
 * backend).
 *
 * É opcional de propósito, e não um passo obrigatório depois do login:
 * o módulo Financeiro funciona sem dispositivo nenhum, e quem ainda
 * está esperando o equipamento chegar não pode ficar trancado numa tela
 * sem saída. A entrada é pela tela de Perfil.
 *
 * Consome vincularDispositivo() de app/src/services/dispositivos.ts
 * (POST /dispositivos/vincular).
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
import { vincularDispositivo } from "../services/dispositivos";
import { ErroHttp } from "../services/api";
import { colors } from "../theme/colors";

const CODIGO_COMPLETO = /^ECO-[A-Z0-9]{4}-[A-Z0-9]{4}$/;

/** Formata o que o produtor digita como ECO-XXXX-XXXX.
 *
 * Aceita colar o código inteiro ou digitar só a parte variável: o
 * prefixo "ECO" é sempre o mesmo, então exigir que ele seja digitado
 * seria trabalho à toa. Letras viram maiúsculas sozinhas, porque a
 * etiqueta é impressa em maiúsculas. */
function mascararCodigo(texto: string): string {
  let limpo = texto.toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (limpo.startsWith("ECO")) limpo = limpo.slice(3);
  limpo = limpo.slice(0, 8);

  if (limpo.length === 0) return "";
  if (limpo.length <= 4) return "ECO-" + limpo;
  return "ECO-" + limpo.slice(0, 4) + "-" + limpo.slice(4);
}

/** Traduz o código HTTP numa frase que diz ao produtor o que fazer. A
 * mensagem crua da API ("Código de pareamento não encontrado") informa
 * o problema, mas não o próximo passo. */
function mensagemDeErro(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.status === 404) {
      return "Código não encontrado. Confira a etiqueta do aparelho: letras e números podem ser confundidos.";
    }
    if (erro.status === 409) {
      return "Este aparelho já está vinculado a outra conta. Se ele é seu, entre em contato com o suporte.";
    }
  }
  return erro instanceof Error ? erro.message : "Não foi possível vincular o aparelho.";
}

export default function VincularDispositivoScreen() {
  const navigation = useNavigation<any>();

  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [vinculado, setVinculado] = useState<string | null>(null);

  const codigoValido = CODIGO_COMPLETO.test(codigo);

  async function handleVincular() {
    setErro(null);

    if (!codigoValido) {
      setErro("Digite o código completo, no formato ECO-XXXX-XXXX.");
      return;
    }

    setCarregando(true);
    try {
      const dispositivo = await vincularDispositivo(codigo);
      setVinculado(dispositivo.nome);
    } catch (e) {
      setErro(mensagemDeErro(e));
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

          <Text style={styles.headerTitulo}>Vincular aparelho</Text>

          <Image
            source={require("../../assets/images/logo-ecovision.png")}
            style={styles.logo}
            resizeMode="contain"
          />

          <View style={styles.divisor} />
        </LinearGradient>

        <View style={styles.formulario}>
          {vinculado ? (
            <View style={styles.sucesso}>
              <Ionicons name="checkmark-circle" size={48} color={colors.oliveGreen} />
              <Text style={styles.sucessoTitulo}>Aparelho vinculado</Text>
              <Text style={styles.sucessoTexto}>
                {vinculado} agora está na sua conta. As leituras e os diagnósticos
                aparecem assim que a primeira captura chegar.
              </Text>

              <TouchableOpacity style={styles.botao} onPress={() => navigation.goBack()}>
                <Text style={styles.botaoTexto}>Voltar ao perfil</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.linkSecundario}
                onPress={() => {
                  setVinculado(null);
                  setCodigo("");
                }}
              >
                <Text style={styles.linkSecundarioTexto}>Vincular outro aparelho</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <Text style={styles.descricao}>
                Digite o código que está na etiqueta do seu equipamento EcoVision.
                Ele vincula o aparelho à sua conta.
              </Text>

              <Text style={styles.label}>Código do aparelho</Text>
              <TextInput
                style={[styles.input, erro && styles.inputErro]}
                placeholder="ECO-XXXX-XXXX"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="characters"
                autoCorrect={false}
                maxLength={13}
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
                  O código não diferencia maiúsculas de minúsculas e não usa as letras
                  O, I e L, para não confundir com zero e um.
                </Text>
              </View>

              <TouchableOpacity
                style={[styles.botao, !codigoValido && styles.botaoDesabilitado]}
                onPress={handleVincular}
                disabled={carregando}
              >
                {carregando ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <Text style={styles.botaoTexto}>Vincular</Text>
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
  input: {
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 18,
    letterSpacing: 2,
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
  linkSecundario: { marginTop: 16 },
  linkSecundarioTexto: { color: colors.oliveGreen, fontWeight: "600", fontSize: 14 },
});
