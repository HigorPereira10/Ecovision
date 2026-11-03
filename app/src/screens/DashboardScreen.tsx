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
import { getDiagnosticosRecentes } from '../services/diagnosticos';
import { LeituraCard } from '../components/LeituraCard';
import { SituacaoSanitariaCard } from '../components/SituacaoSanitariaCard';
import { SerieTemporalCard } from '../components/SerieTemporalCard';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { EstadoVazio } from '../components/EstadoVazio';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { colors } from '../theme/colors';

/**
 * Esta tela foi a última a sair do mock, em 2026-10-11. O card de
 * situação sanitária contava folhas de src/mocks/diagnosticos.json,
 * sempre as mesmas 6, enquanto os cards de temperatura e umidade logo
 * abaixo já mostravam o sensor de verdade. Metade real e metade
 * inventada é pior do que vazia: na banca, um diagnóstico de uma folha
 * que nunca existiu ao lado de 29,5 °C medidos na estufa é exatamente o
 * tipo de coisa que destrói a credibilidade do resto.
 */

interface DiagnosticoResumo {
  saudaveis: number;
  comEstresse: number;
  comDoenca: number;
  /** Fotos reprovadas na guarda de qualidade. Ficam fora das tres
   * contagens acima e aparecem como nota no card. */
  semAnalise: number;
}

interface DadosDashboard {
  leitura: LeituraAmbiental | null;
  historico: LeituraAmbiental[];
  situacao: DiagnosticoResumo;
}

async function buscarDadosDashboard(): Promise<DadosDashboard> {
  const [leitura, historico, diagnosticos] = await Promise.all([
    getUltimaLeitura(),
    getHistoricoLeituras(),
    getDiagnosticosRecentes(),
  ]);

  // Quem decide o que conta como sadio é src/domain/doencas.ts, e o
  // serviço já entrega o campo resolvido. O Dashboard não repete essa
  // regra: ela é a mesma que pinta a cor na tela de Diagnóstico e no
  // card do Histórico, e três cópias dela divergiriam.
  //
  // A contagem é sobre os diagnósticos RECENTES, não sobre o histórico
  // inteiro, e isso é proposital: o card responde "como está a estufa
  // agora", e uma doença resolvida há seis dias continuaria pesando no
  // número se a janela fosse maior.
  // Diagnóstico ausente NÃO entra em nenhuma das duas contagens. O
  // contrário de "saudável" não é "doente" neste sistema: foto
  // reprovada na guarda de qualidade não diz nada sobre a planta, e
  // contá-la como doença encheria o card de alarme falso toda vez que
  // o LED falhasse.
  //
  // Sao TRES estados de planta, nao dois. Ate 2026-11-03 esta contagem
  // era `saudaveis` contra `!saudavel`, e no dia em que a classe
  // estresse_foliar entrou em producao o card passou a exibir "Com
  // doenca (10)" para uma planta que a tela de Diagnostico descreve,
  // duas telas adiante, como alteracao que NAO corresponde a doenca
  // nenhuma do catalogo. Estresse pede atencao, nao pulverizacao.
  const analisados = diagnosticos.filter((d) => !d.semDiagnostico);
  const situacao: DiagnosticoResumo = {
    saudaveis: analisados.filter((d) => d.saudavel).length,
    comEstresse: analisados.filter((d) => d.estresse).length,
    comDoenca: analisados.filter((d) => d.doenca).length,
    semAnalise: diagnosticos.length - analisados.length,
  };

  return { leitura, historico, situacao };
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
    dados.situacao.saudaveis === 0 && dados.situacao.comEstresse === 0 &&
    dados.situacao.comDoenca === 0 && dados.situacao.semAnalise === 0;

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
              <SituacaoSanitariaCard
                saudaveis={dados.situacao.saudaveis}
                comEstresse={dados.situacao.comEstresse}
                comDoenca={dados.situacao.comDoenca}
                semAnalise={dados.situacao.semAnalise}
              />

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