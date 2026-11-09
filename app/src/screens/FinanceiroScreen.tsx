/**
 * Módulo financeiro: seletor de mês, resumo e transações do mês, gráfico
 * por categoria, total geral, registro e exclusão de gastos. Os dados
 * ficam no aparelho (src/services/gastos.ts).
 *
 * Ao trocar de mês, os dados anteriores continuam visíveis e um indicador
 * pequeno aparece ao lado do seletor enquanto o novo mês carrega.
 */

import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  Image,
  ScrollView,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { formatarMoeda } from '../utils/formatarMoeda';
import {
  getGastosPorMes,
  getResumoFinanceiro,
  getGastoTotalGeral,
  registrarGasto,
  excluirGasto,
  Gasto,
  ResumoFinanceiro,
} from '../services/gastos';
import { ResumoFinanceiroCard } from '../components/ResumoFinanceiroCard';
import { GastosPorCategoriaChart } from '../components/GastosPorCategoriaChart';
import { GastoListItem } from '../components/GastoListItem';
import { FormularioGastoModal } from '../components/FormularioGastoModal';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { EstadoVazio } from '../components/EstadoVazio';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { ToastSucesso } from '../components/ToastSucesso';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { useToastSucesso } from '../hooks/useToastSucesso';

const NOMES_MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function formatarMesReferencia(mesReferencia: string): string {
  const [ano, mes] = mesReferencia.split('-');
  return `${NOMES_MESES[Number(mes) - 1]} de ${ano}`;
}

/** Mês selecionado por extenso, em minúsculas, para caber no meio de
 * uma frase ("em outubro de 2026"). */
function formatarMesSelecionado(data: Date): string {
  return `${NOMES_MESES[data.getMonth()].toLowerCase()} de ${data.getFullYear()}`;
}

function inicioDoMes(data: Date): Date {
  return new Date(data.getFullYear(), data.getMonth(), 1);
}

function ehMesmoMesEAno(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

interface DadosFinanceiro {
  gastos: Gasto[];
  resumo: ResumoFinanceiro;
  totalGeral: number;
}

export default function FinanceiroScreen() {
  const [mesSelecionado, setMesSelecionado] = useState<Date>(inicioDoMes(new Date()));

  const buscarDadosFinanceiro = useCallback(async (): Promise<DadosFinanceiro> => {
    const [gastos, resumo, totalGeral] = await Promise.all([
      getGastosPorMes(mesSelecionado),
      getResumoFinanceiro(mesSelecionado),
      getGastoTotalGeral(),
    ]);
    return { gastos, resumo, totalGeral };
  }, [mesSelecionado]);

  const { dados, carregando, atualizando, erro, recarregar, atualizar } =
    useCarregamentoAssincrono(buscarDadosFinanceiro, [mesSelecionado]);

  const [modalVisivel, setModalVisivel] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);
  const { mensagem: mensagemToast, mostrarToast } = useToastSucesso();

  const mesAtual = inicioDoMes(new Date());
  const estaNoMesAtual = ehMesmoMesEAno(mesSelecionado, mesAtual);

  const voltarMes = () => {
    setMesSelecionado((atual) => new Date(atual.getFullYear(), atual.getMonth() - 1, 1));
  };

  const avancarMes = () => {
    if (estaNoMesAtual) return; // não deixa navegar pro futuro
    setMesSelecionado((atual) => new Date(atual.getFullYear(), atual.getMonth() + 1, 1));
  };

  const handleSalvarGasto = async (dadosGasto: {
    categoria: string;
    descricao: string;
    valor: number;
    data: string;
  }) => {
    await registrarGasto(dadosGasto);
    await atualizar();
    mostrarToast('Gasto registrado com sucesso');
  };

  const confirmarExclusao = (gasto: Gasto) => {
    Alert.alert(
      'Excluir gasto',
      `Deseja excluir "${gasto.descricao}" (${gasto.categoria})? Essa ação não pode ser desfeita.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Excluir',
          style: 'destructive',
          onPress: () => handleExcluirGasto(gasto.id),
        },
      ]
    );
  };

  const handleExcluirGasto = async (id: string) => {
    setExcluindoId(id);
    try {
      const removido = await excluirGasto(id);
      if (removido) {
        await atualizar();
        mostrarToast('Gasto excluído');
      } else {
        Alert.alert('Aviso', 'Esse gasto já não existe mais na lista.');
      }
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível excluir o gasto. Tente novamente.');
    } finally {
      setExcluindoId(null);
    }
  };

  // Só bloqueia a tela na primeira carga; ao trocar de mês, um indicador
  // pequeno aparece ao lado do seletor.
  if (carregando && !dados) {
    return <EstadoCarregamento />;
  }

  if (erro && !dados) {
    return <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image
          source={require('../../assets/images/logo-ecovision.png')}
          style={styles.logo}
        />
        <Text style={styles.headerTitulo}>Financeiro</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={atualizando} onRefresh={atualizar} colors={[colors.oliveGreen]} />
        }
      >
        {erro && dados && <AvisoErroInline mensagem={erro} aoTentarNovamente={atualizar} />}

        <View style={styles.seletorMes}>
          <Pressable onPress={voltarMes} hitSlop={10} style={styles.seletorBotao}>
            <Ionicons name="chevron-back" size={20} color={colors.darkGreen} />
          </Pressable>

          <View style={styles.seletorTextoContainer}>
            <Text style={styles.seletorTexto}>
              {dados ? formatarMesReferencia(dados.resumo.mesReferencia) : ''}
            </Text>
            {carregando && dados && (
              <ActivityIndicator size="small" color={colors.oliveGreen} style={styles.seletorSpinner} />
            )}
          </View>

          <Pressable
            onPress={avancarMes}
            disabled={estaNoMesAtual}
            hitSlop={10}
            style={styles.seletorBotao}
          >
            <Ionicons
              name="chevron-forward"
              size={20}
              color={estaNoMesAtual ? colors.textMuted : colors.darkGreen}
            />
          </Pressable>
        </View>

        {dados && (
          <ResumoFinanceiroCard
            totalGasto={dados.resumo.totalGasto}
            quantidadeLancamentos={dados.resumo.quantidadeLancamentos}
            periodo={formatarMesSelecionado(mesSelecionado)}
          />
        )}

        <Text style={styles.totalGeralTexto}>
          Somando todos os meses já registrados: {formatarMoeda(dados?.totalGeral ?? 0)}
        </Text>

        {dados && dados.resumo.porCategoria.length > 0 && (
          <GastosPorCategoriaChart porCategoria={dados.resumo.porCategoria} />
        )}

        <Pressable style={styles.botaoNovoGasto} onPress={() => setModalVisivel(true)}>
          <Text style={styles.botaoNovoGastoTexto}>+ Registrar novo gasto</Text>
        </Pressable>

        <Text style={styles.tituloSecao}>
          Transações de {dados ? formatarMesReferencia(dados.resumo.mesReferencia) : ''}
        </Text>

        {!dados || dados.gastos.length === 0 ? (
          <EstadoVazio
            icone="wallet-outline"
            titulo="Nenhum gasto registrado neste mês"
            subtitulo="Toque em “Registrar novo gasto” para adicionar o primeiro lançamento."
            variante="secao"
          />
        ) : (
          dados.gastos.map((g) => (
            <GastoListItem
              key={g.id}
              gasto={g}
              onExcluir={() => confirmarExclusao(g)}
              excluindo={excluindoId === g.id}
            />
          ))
        )}
      </ScrollView>

      <FormularioGastoModal
        visivel={modalVisivel}
        onFechar={() => setModalVisivel(false)}
        onSalvar={handleSalvarGasto}
      />

      <ToastSucesso mensagem={mensagemToast} />
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
  seletorMes: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
    paddingHorizontal: 4,
  },
  seletorBotao: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.white,
    justifyContent: 'center',
    alignItems: 'center',
  },
  seletorTextoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  seletorTexto: {
    color: colors.textDark,
    fontSize: 16,
    fontWeight: '700',
  },
  seletorSpinner: {
    marginTop: 1,
  },
  totalGeralTexto: {
    color: colors.textMuted,
    fontSize: 12,
    textAlign: 'right',
    marginTop: -4,
    marginBottom: 12,
  },
  botaoNovoGasto: {
    borderWidth: 1,
    borderColor: colors.oliveGreen,
    borderRadius: 24,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 20,
  },
  botaoNovoGastoTexto: {
    color: colors.oliveGreen,
    fontWeight: '700',
    fontSize: 14,
  },
  tituloSecao: {
    color: colors.textDark,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 10,
  },
});