import React, { useCallback } from 'react';
import { View, Text, ScrollView, StyleSheet, Image, Pressable, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { getDispositivos, Dispositivo } from '../services/dispositivos';
import { getPerfilUsuario, PerfilUsuario } from '../services/perfil';
import { logout } from '../services/auth';
import { DispositivoCard } from '../components/DispositivoCard';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { colors } from '../theme/colors';

interface DadosPerfil {
  perfil: PerfilUsuario;
  dispositivos: Dispositivo[];
}

async function buscarDadosPerfil(): Promise<DadosPerfil> {
  const [perfil, dispositivos] = await Promise.all([getPerfilUsuario(), getDispositivos()]);
  return { perfil, dispositivos };
}

export default function PerfilScreen() {
  const navigation = useNavigation<any>();
  const { dados, carregando, erro, recarregar, atualizar } = useCarregamentoAssincrono(buscarDadosPerfil, []);

  // Atualiza ao voltar da tela de vínculo: sem isto, o aparelho
  // recém-vinculado só apareceria no próximo reinício do app.
  //
  // `atualizar` e não `recarregar`: o primeiro busca em segundo plano,
  // mantendo o conteúdo na tela, enquanto o segundo levanta o estado de
  // carregamento e apagaria o perfil por um instante a cada vez que a
  // aba ganha foco.
  useFocusEffect(
    useCallback(() => {
      atualizar();
    }, [atualizar])
  );

  if (carregando && !dados) {
    return <EstadoCarregamento />;
  }

  if (erro && !dados) {
    return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  }

  function confirmarLogout() {
    Alert.alert('Sair da conta', 'Tem certeza que deseja sair?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Sair', style: 'destructive', onPress: () => logout() },
    ]);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image source={require('../../assets/images/logo-ecovision.png')} style={styles.logo} />
        <Text style={styles.headerTitulo}>Perfil</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {erro && dados && <AvisoErroInline mensagem={erro} aoTentarNovamente={atualizar} />}

        {dados && (
          <>
            <View style={styles.cardUsuario}>
              <View style={styles.avatar}>
                <Ionicons name="person" size={28} color={colors.darkGreen} />
              </View>
              <View>
                <Text style={styles.nomeUsuario}>{dados.perfil.nome}</Text>
                <Text style={styles.emailUsuario}>{dados.perfil.email}</Text>
              </View>
            </View>

            <Text style={styles.tituloSecao}>Dispositivos IoT</Text>

            {dados.dispositivos.length === 0 ? (
              <View style={styles.semDispositivo}>
                <Ionicons name="hardware-chip-outline" size={32} color={colors.textMuted} />
                <Text style={styles.semDispositivoTexto}>
                  Nenhum aparelho vinculado ainda. Vincule o seu para ver as leituras
                  e os diagnósticos da sua estufa.
                </Text>
              </View>
            ) : (
              dados.dispositivos.map((d) => (
                <DispositivoCard key={d.id} dispositivo={d} />
              ))
            )}

            <Pressable
              style={styles.botaoVincular}
              onPress={() => navigation.navigate('VincularDispositivo')}
            >
              <Ionicons name="add-circle-outline" size={18} color={colors.white} />
              <Text style={styles.botaoVincularTexto}>Vincular aparelho</Text>
            </Pressable>

            <Pressable style={styles.botaoSair} onPress={confirmarLogout}>
              <Ionicons name="log-out-outline" size={18} color={colors.danger} />
              <Text style={styles.botaoSairTexto}>Sair da conta</Text>
            </Pressable>

            <Text style={styles.rodape}>
              EcoVision · TCC UNIP 2026 · Amanda Camille, Higor Pereira, Igor Rodrigues e João Paulo
            </Text>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.cream,
  },
  header: {
    backgroundColor: colors.darkGreen,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 50,
    paddingBottom: 16,
  },
  logo: {
    width: 32,
    height: 32,
    resizeMode: 'contain',
  },
  headerTitulo: {
    color: colors.white,
    fontSize: 18,
    fontWeight: '700',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 12,
    paddingBottom: 32,
  },
  cardUsuario: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.textOnDark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nomeUsuario: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textDark,
  },
  emailUsuario: {
    fontSize: 13,
    color: colors.oliveGreen,
    marginTop: 2,
  },
  tituloSecao: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.darkGreen,
    marginBottom: 10,
  },
  semDispositivo: {
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingVertical: 24,
    paddingHorizontal: 20,
    gap: 10,
  },
  semDispositivoTexto: {
    fontSize: 13,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 19,
  },
  botaoVincular: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: colors.oliveGreen,
    borderRadius: 30,
    paddingVertical: 14,
    marginTop: 16,
  },
  botaoVincularTexto: { color: colors.white, fontSize: 15, fontWeight: '700' },
  botaoSair: {
    borderWidth: 1,
    borderColor: colors.danger,
    borderRadius: 12,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 8,
  },
  botaoSairTexto: {
    color: colors.danger,
    fontWeight: '700',
    fontSize: 15,
  },
  rodape: {
    fontSize: 11,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: 20,
  },
});