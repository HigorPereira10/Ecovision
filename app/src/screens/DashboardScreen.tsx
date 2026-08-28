import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Image,
} from 'react-native';
import { getUltimaLeitura, getHistoricoLeituras, LeituraAmbiental } from '../services/leituras';
import { LeituraCard } from '../components/LeituraCard';
import { SituacaoSanitariaCard } from '../components/SituacaoSanitariaCard';
import { SerieTemporalCard } from '../components/SerieTemporalCard';
import { colors } from '../theme/colors';

// TODO: ajustar quando confirmarmos o schema real de diagnosticos.json
import diagnosticosMock from '../mocks/diagnosticos.json';

interface DiagnosticoResumo {
  saudaveis: number;
  comDoenca: number;
}

function calcularSituacaoSanitaria(): DiagnosticoResumo {
  const diagnosticos = diagnosticosMock as any[];
  let saudaveis = 0;
  let comDoenca = 0;

  diagnosticos.forEach((d) => {
    const classificacaoNormalizada = (d.classificacao || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, ''); // remove acentos

    if (classificacaoNormalizada.includes('saudavel')) {
      saudaveis++;
    } else {
      comDoenca++;
    }
  });

  return { saudaveis, comDoenca };
}

export default function DashboardScreen() {
  const [leitura, setLeitura] = useState<LeituraAmbiental | null>(null);
  const [historico, setHistorico] = useState<LeituraAmbiental[]>([]);
  const [situacao, setSituacao] = useState<DiagnosticoResumo>({ saudaveis: 0, comDoenca: 0 });
  const [carregando, setCarregando] = useState(true);
  const [atualizando, setAtualizando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregarDados = useCallback(async () => {
    try {
      setErro(null);
      const [ultima, hist] = await Promise.all([getUltimaLeitura(), getHistoricoLeituras()]);
      setLeitura(ultima);
      setHistorico(hist);
      setSituacao(calcularSituacaoSanitaria());
    } catch (e) {
      setErro('Não foi possível carregar os dados do painel.');
    }
  }, []);

  useEffect(() => {
    (async () => {
      setCarregando(true);
      await carregarDados();
      setCarregando(false);
    })();
  }, [carregarDados]);

  const onRefresh = async () => {
    setAtualizando(true);
    await carregarDados();
    setAtualizando(false);
  };

  if (carregando) {
    return (
      <View style={styles.centro}>
        <ActivityIndicator size="large" color={colors.oliveGreen} />
      </View>
    );
  }

  if (erro) {
    return (
      <View style={styles.centro}>
        <Text style={styles.erroTexto}>{erro}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image
          source={require('../../assets/images/logo-ecovision.png')}
          style={styles.logo}
        />
        <Text style={styles.headerTitulo}>Início</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={atualizando} onRefresh={onRefresh} colors={[colors.oliveGreen]} />
        }
      >
        <SituacaoSanitariaCard saudaveis={situacao.saudaveis} comDoenca={situacao.comDoenca} />

        {leitura && (
          <View style={styles.linhaCards}>
            <LeituraCard titulo="Temperatura" valor={leitura.temperatura} unidade="°C" icone="🌡️" />
            <LeituraCard titulo="Umid. ar" valor={leitura.umidade_ar} unidade="%" icone="💧" />
            <LeituraCard titulo="Umid. solo" valor={leitura.umidade_solo} unidade="%" icone="🌱" />
          </View>
        )}

        <SerieTemporalCard leituras={historico} />
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
  },
  linhaCards: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  centro: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
  },
  erroTexto: {
    color: colors.danger,
    fontSize: 15,
    textAlign: 'center',
    paddingHorizontal: 24,
  },
});