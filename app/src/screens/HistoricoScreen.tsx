/**
 * app/src/screens/HistoricoScreen.tsx
 *
 * Tela de Histórico: diagnósticos e leituras ambientais passadas, com
 * filtro por período e por campo (dispositivo). Segue o mesmo padrão
 * de camada de dados do DashboardScreen — nunca lê os JSONs direto,
 * sempre via services/.
 *
 * Loading/erro/refresh padronizados via useCarregamentoAssincrono
 * (mesmo hook usado nas outras telas).
 *
 * Header sem botão de voltar por enquanto (a ser implementado quando
 * a navegação para esta tela deixar de ser só pela tab bar).
 */

import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Image,
  RefreshControl,
} from 'react-native';

import { colors } from '../theme/colors';
import { getHistoricoLeituras, LeituraAmbiental } from '../services/leituras';
import {
  getDiagnosticos,
  getImagemDoRegistro,
  getDispositivoIdUnico,
  Diagnostico,
} from '../services/diagnosticos';
import { FiltroDropdown } from '../components/FiltroDropdown';
import { UmidadeBarChart } from '../components/UmidadeBarChart';
import { DiagnosticoHistoricoCard } from '../components/DiagnosticoHistoricoCard';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { OPCOES_PERIODO, filtrarPorPeriodo } from '../utils/periodo';

const OPCAO_TODOS_CAMPOS = { valor: 'todos', rotulo: 'Todos os campos' };

interface DiagnosticoComImagem extends Diagnostico {
  caminhoImagem: string | null;
}

interface DadosHistorico {
  leituras: LeituraAmbiental[];
  diagnosticos: DiagnosticoComImagem[];
}

async function buscarDadosHistorico(): Promise<DadosHistorico> {
  const [leituras, diagnosticos] = await Promise.all([getHistoricoLeituras(), getDiagnosticos()]);

  const diagnosticosComImagem: DiagnosticoComImagem[] = await Promise.all(
    diagnosticos.map(async (d) => {
      const imagem = await getImagemDoRegistro(d.registro_imagem_id);
      const caminho = imagem?.caminho_arquivo ?? null;
      // Só usamos a imagem se for URL remota (http/https). Caminhos
      // locais de mock não são resolvíveis dinamicamente pelo Metro —
      // ver nota em services/diagnosticos.ts.
      const caminhoValido = caminho && /^https?:\/\//.test(caminho) ? caminho : null;
      return { ...d, caminhoImagem: caminhoValido };
    })
  );

  return { leituras, diagnosticos: diagnosticosComImagem };
}

export default function HistoricoScreen() {
  const { dados, carregando, atualizando, erro, recarregar, atualizar } =
    useCarregamentoAssincrono(buscarDadosHistorico, []);

  // TODO: trocar padrão para '48h' quando os mocks estiverem com
  // timestamps relativos à data atual (hoje os mocks são de ago/2026).
  const [periodoSelecionado, setPeriodoSelecionado] = useState('todos');
  const [campoSelecionado, setCampoSelecionado] = useState('todos');

  const leituras = dados?.leituras ?? [];
  const diagnosticos = dados?.diagnosticos ?? [];

  const opcoesCampo = useMemo(() => {
    const idsUnicos = Array.from(new Set(leituras.map((l) => l.dispositivo_id)));
    return [
      OPCAO_TODOS_CAMPOS,
      ...idsUnicos.map((id) => ({ valor: String(id), rotulo: `Estufa ${id}` })),
    ];
  }, [leituras]);

  const horasSelecionadas =
    OPCOES_PERIODO.find((o) => o.valor === periodoSelecionado)?.horas ?? null;
  const dispositivoUnicoId = getDispositivoIdUnico();

  const leiturasFiltradas = useMemo(() => {
    let resultado = filtrarPorPeriodo(leituras, (l) => l.timestamp, horasSelecionadas);
    if (campoSelecionado !== 'todos') {
      resultado = resultado.filter((l) => String(l.dispositivo_id) === campoSelecionado);
    }
    return resultado;
  }, [leituras, horasSelecionadas, campoSelecionado]);

  const diagnosticosFiltrados = useMemo(() => {
    let resultado = filtrarPorPeriodo(diagnosticos, (d) => d.timestamp, horasSelecionadas);
    if (campoSelecionado !== 'todos' && campoSelecionado !== String(dispositivoUnicoId)) {
      resultado = [];
    }
    return resultado;
  }, [diagnosticos, horasSelecionadas, campoSelecionado, dispositivoUnicoId]);

  if (carregando && !dados) {
    return <EstadoCarregamento />;
  }

  if (erro && !dados) {
    return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image source={require('../../assets/images/logo-ecovision.png')} style={styles.logo} />
        <Text style={styles.headerTitulo}>Seu Histórico</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={atualizando} onRefresh={atualizar} colors={[colors.oliveGreen]} />
        }
      >
        <View style={styles.linhaFiltros}>
          <FiltroDropdown
            icone="calendar-outline"
            opcoes={OPCOES_PERIODO.map((o) => ({ valor: o.valor, rotulo: o.rotulo }))}
            valorSelecionado={periodoSelecionado}
            onSelecionar={setPeriodoSelecionado}
          />
          <View style={{ width: 8 }} />
          <FiltroDropdown
            icone="location-outline"
            opcoes={opcoesCampo}
            valorSelecionado={campoSelecionado}
            onSelecionar={setCampoSelecionado}
          />
        </View>

        {erro && dados && <AvisoErroInline mensagem={erro} aoTentarNovamente={atualizar} />}

        <UmidadeBarChart leituras={leiturasFiltradas} />

        <Text style={styles.secaoTitulo}>Diagnósticos de campo</Text>
        {diagnosticosFiltrados.length === 0 ? (
          <Text style={styles.vazioTexto}>Nenhum diagnóstico no período selecionado.</Text>
        ) : (
          diagnosticosFiltrados.map((d) => (
            <DiagnosticoHistoricoCard key={d.id} diagnostico={d} caminhoImagem={d.caminhoImagem} />
          ))
        )}

        <Text style={styles.secaoTitulo}>Leituras ambientais</Text>
        {leiturasFiltradas.length === 0 ? (
          <Text style={styles.vazioTexto}>Nenhuma leitura no período selecionado.</Text>
        ) : (
          leiturasFiltradas.map((l) => (
            <View key={l.id} style={styles.leituraItem}>
              <Text style={styles.leituraData}>
                {new Date(l.timestamp).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                {'  ·  '}
                {new Date(l.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </Text>
              <Text style={styles.leituraValores}>
                {l.temperatura}°C · ar {l.umidade_ar}% · solo {l.umidade_solo}%
              </Text>
            </View>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
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
  scroll: { flex: 1 },
  scrollContent: { padding: 12, paddingBottom: 24 },
  linhaFiltros: { flexDirection: 'row', marginBottom: 12 },
  secaoTitulo: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textDark,
    marginBottom: 8,
    marginTop: 4,
  },
  vazioTexto: { fontSize: 13, color: colors.textMuted, marginBottom: 12 },
  leituraItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.white,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 8,
  },
  leituraData: { fontSize: 13, color: colors.textDark, fontWeight: '600' },
  leituraValores: { fontSize: 13, color: colors.textMuted },
});
