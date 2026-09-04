/**
 * app/src/screens/FinanceiroScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Tela financeira MOCK (Blueprint v3.0, Semana 3 do cronograma):
 * seletor de mês, resumo e transações do mês selecionado, gráfico por
 * categoria, total geral (todos os períodos), formulário de registro
 * de gasto e exclusão de gastos.
 *
 * Dados persistidos em AsyncStorage (ver src/services/gastos.ts),
 * semeados a partir do mock `gastos.json` na primeira execução.
 *
 * Header customizado (logo + título) igual ao padrão do Dashboard —
 * headerShown: false precisa estar setado no Tab.Screen "Financeiro"
 * no AppNavigator para não duplicar o header nativo.
 */

import React, { useCallback, useEffect, useState } from 'react';
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

const NOMES_MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function formatarMesReferencia(mesReferencia: string): string {
  const [ano, mes] = mesReferencia.split('-');
  return `${NOMES_MESES[Number(mes) - 1]} de ${ano}`;
}

function inicioDoMes(data: Date): Date {
  return new Date(data.getFullYear(), data.getMonth(), 1);
}

function ehMesmoMesEAno(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

export default function FinanceiroScreen() {
  const [mesSelecionado, setMesSelecionado] = useState<Date>(inicioDoMes(new Date()));
  const [gastos, setGastos] = useState<Gasto[]>([]);
  const [resumo, setResumo] = useState<ResumoFinanceiro | null>(null);
  const [totalGeral, setTotalGeral] = useState<number>(0);
  const [carregando, setCarregando] = useState(true);
  const [atualizando, setAtualizando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [modalVisivel, setModalVisivel] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  const carregarDados = useCallback(async () => {
    try {
      setErro(null);
      const [listaGastos, resumoFinanceiro, totalGeralAtual] = await Promise.all([
        getGastosPorMes(mesSelecionado),
        getResumoFinanceiro(mesSelecionado),
        getGastoTotalGeral(),
      ]);
      setGastos(listaGastos);
      setResumo(resumoFinanceiro);
      setTotalGeral(totalGeralAtual);
    } catch (e) {
      setErro('Não foi possível carregar os dados financeiros.');
    }
  }, [mesSelecionado]);

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

  const mesAtual = inicioDoMes(new Date());
  const estaNoMesAtual = ehMesmoMesEAno(mesSelecionado, mesAtual);

  const voltarMes = () => {
    setMesSelecionado((atual) => new Date(atual.getFullYear(), atual.getMonth() - 1, 1));
  };

  const avancarMes = () => {
    if (estaNoMesAtual) return; // não deixa navegar pro futuro
    setMesSelecionado((atual) => new Date(atual.getFullYear(), atual.getMonth() + 1, 1));
  };

  const handleSalvarGasto = async (dados: {
    categoria: string;
    descricao: string;
    valor: number;
    data: string;
  }) => {
    await registrarGasto(dados);
    await carregarDados();
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
        await carregarDados();
      } else {
        Alert.alert('Aviso', 'Esse gasto já não existe mais na lista.');
      }
    } catch (e) {
      Alert.alert('Erro', 'Não foi possível excluir o gasto. Tente novamente.');
    } finally {
      setExcluindoId(null);
    }
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
        <Text style={styles.headerTitulo}>Financeiro</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={atualizando} onRefresh={onRefresh} colors={[colors.oliveGreen]} />
        }
      >
        <View style={styles.seletorMes}>
          <Pressable onPress={voltarMes} hitSlop={10} style={styles.seletorBotao}>
            <Ionicons name="chevron-back" size={20} color={colors.darkGreen} />
          </Pressable>

          <Text style={styles.seletorTexto}>
            {resumo ? formatarMesReferencia(resumo.mesReferencia) : ''}
          </Text>

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

        {resumo && (
          <ResumoFinanceiroCard
            totalGasto={resumo.totalGasto}
            quantidadeLancamentos={resumo.quantidadeLancamentos}
          />
        )}

        <Text style={styles.totalGeralTexto}>
          Total geral (todos os períodos): {formatarMoeda(totalGeral)}
        </Text>

        {resumo && resumo.porCategoria.length > 0 && (
          <GastosPorCategoriaChart porCategoria={resumo.porCategoria} />
        )}

        <Pressable style={styles.botaoNovoGasto} onPress={() => setModalVisivel(true)}>
          <Text style={styles.botaoNovoGastoTexto}>+ Registrar novo gasto</Text>
        </Pressable>

        <Text style={styles.tituloSecao}>
          Transações de {resumo ? formatarMesReferencia(resumo.mesReferencia) : ''}
        </Text>

        {gastos.length === 0 ? (
          <Text style={styles.vazio}>Nenhum gasto registrado neste mês.</Text>
        ) : (
          gastos.map((g) => (
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
  seletorTexto: {
    color: colors.textDark,
    fontSize: 16,
    fontWeight: '700',
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
  vazio: {
    color: colors.textMuted,
    fontSize: 13,
    textAlign: 'center',
    paddingVertical: 20,
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
