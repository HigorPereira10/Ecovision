/**
 * Tela de Histórico: diagnósticos e leituras ambientais, com filtros por
 * período e por campo (dispositivo). Os dois filtros comparam o device_id
 * de cada item.
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
import { getDiagnosticos, Diagnostico } from '../services/diagnosticos';
import { FiltroDropdown } from '../components/FiltroDropdown';
import { DistribuicaoDiagnosticosCard } from '../components/DistribuicaoDiagnosticosCard';
import { DiagnosticoHistoricoCard } from '../components/DiagnosticoHistoricoCard';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { EstadoVazio } from '../components/EstadoVazio';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { OPCOES_PERIODO, filtrarPorPeriodo } from '../utils/periodo';

const OPCAO_TODOS_CAMPOS = { valor: 'todos', rotulo: 'Todos os campos' };

/** Monta o texto de uma leitura omitindo as medições ausentes (sensor com
 * falha), em vez de exibir unidades vazias ou um zero que pareceria
 * medição. */
function descreverLeitura(l: LeituraAmbiental): string {
  const partes: string[] = [];
  if (l.temperatura !== null) partes.push(`${l.temperatura}°C`);
  if (l.umidade_ar !== null) partes.push(`ar ${l.umidade_ar}%`);
  if (l.umidade_solo !== null) partes.push(`solo ${l.umidade_solo}%`);

  if (partes.length === 0) return 'Nenhum sensor respondeu neste ciclo';
  return partes.join('  ·  ');
}

interface DadosHistorico {
  leituras: LeituraAmbiental[];
  diagnosticos: Diagnostico[];
}

async function buscarDadosHistorico(): Promise<DadosHistorico> {
  // Em paralelo porque são duas rotas independentes: em série, a tela
  // esperaria a soma das duas latências sem precisar. Sem corte de período
  // (null): os filtros da tela só alcançam o que foi baixado, e "Todo o
  // período" precisa do histórico inteiro.
  const [leituras, diagnosticos] = await Promise.all([
    getHistoricoLeituras(null),
    getDiagnosticos(null),
  ]);
  return { leituras, diagnosticos };
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

  // As opções do filtro vêm das leituras e dos diagnósticos, para incluir
  // dispositivos que enviaram fotos sem leituras. O rótulo é o próprio
  // device_id, o mesmo exibido no Perfil.
  const opcoesCampo = useMemo(() => {
    const idsUnicos = Array.from(
      new Set([
        ...leituras.map((l) => l.dispositivo_id),
        ...diagnosticos.map((d) => d.dispositivo_id),
      ]),
    ).sort();
    return [OPCAO_TODOS_CAMPOS, ...idsUnicos.map((id) => ({ valor: id, rotulo: id }))];
  }, [leituras, diagnosticos]);

  const opcaoPeriodo = OPCOES_PERIODO.find((o) => o.valor === periodoSelecionado);
  const horasSelecionadas = opcaoPeriodo?.horas ?? null;
  const rotuloPeriodo = opcaoPeriodo?.rotulo ?? 'Todo o período';

  const leiturasFiltradas = useMemo(() => {
    let resultado = filtrarPorPeriodo(leituras, (l) => l.timestamp, horasSelecionadas);
    if (campoSelecionado !== 'todos') {
      resultado = resultado.filter((l) => String(l.dispositivo_id) === campoSelecionado);
    }
    return resultado;
  }, [leituras, horasSelecionadas, campoSelecionado]);

  const diagnosticosFiltrados = useMemo(() => {
    let resultado = filtrarPorPeriodo(diagnosticos, (d) => d.timestamp, horasSelecionadas);
    if (campoSelecionado !== 'todos') {
      resultado = resultado.filter((d) => d.dispositivo_id === campoSelecionado);
    }
    return resultado;
  }, [diagnosticos, horasSelecionadas, campoSelecionado]);

  if (carregando && !dados) {
    return <EstadoCarregamento />;
  }

  if (erro && !dados) {
    return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  }

  const filtroAtivo = periodoSelecionado !== 'todos' || campoSelecionado !== 'todos';

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

        <DistribuicaoDiagnosticosCard
          diagnosticos={diagnosticosFiltrados}
          rotuloPeriodo={rotuloPeriodo}
          rotuloCampo={campoSelecionado === 'todos' ? undefined : campoSelecionado}
        />

        {diagnosticosFiltrados.length > 0 && (
          <Text style={styles.secaoTitulo}>Diagnósticos de campo</Text>
        )}
        {diagnosticosFiltrados.map((d) => (
          <DiagnosticoHistoricoCard key={d.id} diagnostico={d} />
        ))}

        <Text style={styles.secaoTitulo}>Leituras ambientais</Text>
        {leiturasFiltradas.length === 0 ? (
          <EstadoVazio
            icone="water-outline"
            titulo="Nenhuma leitura no período selecionado"
            subtitulo={filtroAtivo ? 'Tente ampliar o período ou trocar o campo selecionado.' : undefined}
            variante="secao"
          />
        ) : (
          leiturasFiltradas.map((l) => (
            <View key={l.id} style={styles.leituraItem}>
              <Text style={styles.leituraData}>
                {new Date(l.timestamp).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })}
                {'  ·  '}
                {new Date(l.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </Text>
              <Text style={styles.leituraValores}>{descreverLeitura(l)}</Text>
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