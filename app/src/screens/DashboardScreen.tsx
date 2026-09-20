import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  Image,
} from 'react-native';
import { getUltimaLeitura, getHistoricoLeituras, LeituraAmbiental } from '../services/leituras';
import { LeituraCard } from '../components/LeituraCard';
import { SituacaoSanitariaCard } from '../components/SituacaoSanitariaCard';
import { SerieTemporalCard } from '../components/SerieTemporalCard';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { EstadoVazio } from '../components/EstadoVazio';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { colors } from '../theme/colors';

// TODO: ajustar quando confirmarmos o schema real de diagnosticos.json
import diagnosticosMock from '../mocks/diagnosticos.json';

interface DiagnosticoResumo {
  saudaveis: number;
  comDoenca: number;
}

interface DadosDashboard {
  leitura: LeituraAmbiental | null;
  historico: LeituraAmbiental[];
  situacao: DiagnosticoResumo;
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

async function buscarDadosDashboard(): Promise<DadosDashboard> {
  const [leitura, historico] = await Promise.all([getUltimaLeitura(), getHistoricoLeituras()]);
  return { leitura, historico, situacao: calcularSituacaoSanitaria() };
}

export default function DashboardScreen() {
  const { dados, carregando, atualizando, erro, recarregar, atualizar } =
    useCarregamentoAssincrono(buscarDadosDashboard, []);

  // Carga inicial ainda não terminou e não há nada na tela ainda.
  if (carregando && !dados) {
    return <EstadoCarregamento />;
  }

  // Carga inicial falhou e não há nada na tela pra mostrar.
  if (erro && !dados) {
    return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  }

  // Dispositivo existe mas ainda não enviou nenhuma leitura nem gerou
  // nenhum diagnóstico — cenário plausível logo após o cadastro do
  // sensor, antes do IoT começar a reportar dados.
  const semNenhumDado =
    dados && !dados.leitura && dados.historico.length === 0 &&
    dados.situacao.saudaveis === 0 && dados.situacao.comDoenca === 0;

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
          <RefreshControl refreshing={atualizando} onRefresh={atualizar} colors={[colors.oliveGreen]} />
        }
      >
        {/* Refresh falhou mas ainda temos os últimos dados bons na tela */}
        {erro && dados && <AvisoErroInline mensagem={erro} aoTentarNovamente={atualizar} />}

        {semNenhumDado ? (
          <EstadoVazio
            icone="leaf-outline"
            titulo="Nenhuma leitura recebida ainda"
            subtitulo="Assim que o dispositivo começar a enviar dados da estufa, eles aparecem aqui."
            variante="secao"
          />
        ) : (
          dados && (
            <>
              <SituacaoSanitariaCard saudaveis={dados.situacao.saudaveis} comDoenca={dados.situacao.comDoenca} />

              {dados.leitura && (
                <View style={styles.linhaCards}>
                  <LeituraCard
                    titulo="Temperatura"
                    valor={dados.leitura.temperatura}
                    unidade="°C"
                    icone="thermometer-outline"
                    cor={colors.laranjaTemperatura}
                  />
                  <LeituraCard
                    titulo="Umid. ar"
                    valor={dados.leitura.umidade_ar}
                    unidade="%"
                    icone="water-outline"
                    cor={colors.azulUmidade}
                  />
                  <LeituraCard
                    titulo="Umid. solo"
                    valor={dados.leitura.umidade_solo}
                    unidade="%"
                    icone="leaf-outline"
                    cor={colors.oliveGreen}
                  />
                </View>
              )}

              <SerieTemporalCard leituras={dados.historico} />
            </>
          )
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
  },
  linhaCards: {
    flexDirection: 'row',
    marginBottom: 12,
  },
});