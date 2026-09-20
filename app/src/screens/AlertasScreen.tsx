/**
 * app/src/screens/AlertasScreen.tsx
 *
 * Tela de Alertas: lista de alertas, filtráveis por severidade
 * (Crítico / Cuidado / Informativo), com status lido/não lido e ação
 * "Marcar como lido".
 *
 * Os dados vêm de services/alertas.ts (camada de serviço), nunca do
 * JSON mockado diretamente — quando a API do Higor estiver pronta,
 * só a implementação interna de getAlertas()/marcarAlertaLido() muda
 * (PATCH /alertas/{id}/lido), esta tela não precisa ser tocada.
 *
 * Loading/erro/refresh padronizados via useCarregamentoAssincrono
 * (mesmo hook usado nas outras telas). "Marcar como lido" tem seu
 * próprio tratamento de erro local (erroMarcarLido), separado do erro
 * de carregamento da lista — uma falha ao marcar não deve esconder a
 * lista inteira. Um sucesso ao marcar mostra um toast leve
 * (useToastSucesso) como confirmação visual.
 *
 * Header customizado (logo + título) segue o mesmo padrão do
 * DashboardScreen, a aba "Alertas" no AppNavigator precisa estar com
 * headerShown: false, senão aparecem dois headers sobrepostos (mesmo
 * problema já resolvido no DiagnosticoScreen).
 *
 * Notificações locais (Dia 22-23, Blueprint Fase 5): o botão de sino
 * no header dispara uma notificação de demonstração
 * (dispararNotificacaoTeste), e useFocusEffect roda uma verificação
 * automática (verificarNovosAlertasNaoLidos) toda vez que a tela ganha
 * foco, simulando o que futuramente será um push real vindo do
 * backend. Ver services/notificacoes.ts para detalhes.
 */
import React, { useMemo, useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, Pressable, Image, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { getAlertas, marcarAlertaLido, Alerta, SeveridadeAlerta } from '../services/alertas';
import {
  inicializarNotificacoes,
  dispararNotificacaoTeste,
  verificarNovosAlertasNaoLidos,
} from '../services/notificacoes';
import { EstadoCarregamento } from '../components/EstadoCarregamento';
import { EstadoErro } from '../components/EstadoErro';
import { EstadoVazio } from '../components/EstadoVazio';
import { AvisoErroInline } from '../components/AvisoErroInline';
import { ToastSucesso } from '../components/ToastSucesso';
import { useCarregamentoAssincrono } from '../hooks/useCarregamentoAssincrono';
import { useToastSucesso } from '../hooks/useToastSucesso';
import { colors } from '../theme/colors';

type Filtro = 'todos' | SeveridadeAlerta;

const SEVERIDADE_CONFIG: Record<SeveridadeAlerta, { label: string; cor: string; icone: keyof typeof Ionicons.glyphMap }> = {
  critico: { label: 'Crítico', cor: colors.danger, icone: 'warning' },
  cuidado: { label: 'Cuidado', cor: colors.cuidado, icone: 'warning' },
  informativo: { label: 'Informativo', cor: colors.informativo, icone: 'information-circle' },
};

const FILTROS: { chave: Filtro; label: string }[] = [
  { chave: 'todos', label: 'Todos' },
  { chave: 'critico', label: 'Crítico' },
  { chave: 'cuidado', label: 'Cuidado' },
  { chave: 'informativo', label: 'Informativo' },
];

function formatarData(timestamp: string) {
  const data = new Date(timestamp);
  const dataStr = data.toLocaleDateString('pt-BR');
  const horaStr = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${dataStr}, ${horaStr}`;
}

export default function AlertasScreen() {
  const { dados: alertas, carregando, atualizando, erro, recarregar, atualizar } =
    useCarregamentoAssincrono(getAlertas, []);

  const [filtro, setFiltro] = useState<Filtro>('todos');
  const [marcandoId, setMarcandoId] = useState<number | null>(null);
  const [erroMarcarLido, setErroMarcarLido] = useState<string | null>(null);
  const { mensagem: mensagemToast, mostrarToast } = useToastSucesso();

  // Verificação automática de novos alertas não lidos toda vez que a
  // tela ganha foco — simula, do lado do app, o que futuramente será
  // um evento de push vindo do backend (Blueprint Fase 5).
  useFocusEffect(
    useCallback(() => {
      inicializarNotificacoes();
      verificarNovosAlertasNaoLidos();
    }, [])
  );

  async function marcarComoLido(id: number) {
    setMarcandoId(id);
    setErroMarcarLido(null);
    try {
      await marcarAlertaLido(id);
      // Refaz a busca pra refletir o estado persistido pelo serviço —
      // no futuro, pelo backend real, que passa a ser a fonte da verdade.
      await atualizar();
      mostrarToast('Alerta marcado como lido');
    } catch (e) {
      setErroMarcarLido('Não foi possível marcar como lido. Tente novamente.');
    } finally {
      setMarcandoId(null);
    }
  }

  const alertasFiltrados = useMemo(
    () => (!alertas ? [] : filtro === 'todos' ? alertas : alertas.filter((a) => a.severidade === filtro)),
    [alertas, filtro]
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image source={require('../../assets/images/logo-ecovision.png')} style={styles.logo} />
        <Text style={styles.headerTitulo}>Seus Alertas</Text>
        <Pressable onPress={dispararNotificacaoTeste} hitSlop={8}>
          <Ionicons name="notifications-outline" size={24} color={colors.white} />
        </Pressable>
      </View>

      <View style={styles.filtrosContainer}>
        {FILTROS.map((f) => {
          const selecionado = filtro === f.chave;
          const cor = f.chave === 'todos' ? colors.oliveGreen : SEVERIDADE_CONFIG[f.chave as SeveridadeAlerta].cor;
          return (
            <Pressable
              key={f.chave}
              onPress={() => setFiltro(f.chave)}
              style={[
                styles.filtroChip,
                selecionado && f.chave === 'todos' && { backgroundColor: colors.oliveGreen, borderColor: colors.oliveGreen },
                selecionado && f.chave !== 'todos' && { borderColor: cor },
              ]}
            >
              {f.chave !== 'todos' && <View style={[styles.filtroDot, { backgroundColor: cor }]} />}
              <Text
                style={[
                  styles.filtroTexto,
                  selecionado && f.chave === 'todos' && { color: colors.white },
                  selecionado && f.chave !== 'todos' && { color: cor },
                ]}
              >
                {f.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {carregando && !alertas ? (
        <EstadoCarregamento />
      ) : erro && !alertas ? (
        <EstadoErro mensagem={erro} aoTentarNovamente={recarregar} />
      ) : (
        <FlatList
          style={styles.lista}
          contentContainerStyle={styles.listaConteudo}
          data={alertasFiltrados}
          keyExtractor={(item) => String(item.id)}
          refreshing={atualizando}
          onRefresh={atualizar}
          ListHeaderComponent={
            (erro && alertas) || erroMarcarLido ? (
              <View>
                {erro && alertas && <AvisoErroInline mensagem={erro} aoTentarNovamente={atualizar} />}
                {erroMarcarLido && <AvisoErroInline mensagem={erroMarcarLido} />}
              </View>
            ) : null
          }
          ListEmptyComponent={
            <EstadoVazio
              icone="notifications-off-outline"
              titulo={filtro === 'todos' ? 'Nenhum alerta ainda' : 'Nenhum alerta nesta categoria'}
              subtitulo={
                filtro === 'todos'
                  ? 'Quando algo pedir atenção na sua estufa, o alerta aparece aqui.'
                  : 'Tente outro filtro de severidade para ver os demais alertas.'
              }
              variante="secao"
            />
          }
          renderItem={({ item }) => {
            const config = SEVERIDADE_CONFIG[item.severidade];
            const marcandoEsteItem = marcandoId === item.id;
            return (
              <View style={styles.card}>
                <View style={[styles.faixa, { backgroundColor: config.cor }]}>
                  <View style={styles.faixaEsquerda}>
                    <Ionicons name={config.icone} size={16} color={colors.white} />
                    <Text style={styles.faixaTexto}>{config.label}</Text>
                  </View>
                  {!item.lido && (
                    <View style={styles.novoBadge}>
                      <Text style={styles.novoTexto}>novo</Text>
                    </View>
                  )}
                </View>

                <View style={styles.corpo}>
                  <Text style={styles.titulo}>{item.titulo}</Text>
                  <Text style={[styles.descricao, { color: config.cor }]}>{item.descricao}</Text>
                  <Text style={styles.data}>{formatarData(item.timestamp)}</Text>

                  <Pressable
                    style={[styles.botao, item.lido && styles.botaoLido]}
                    onPress={() => marcarComoLido(item.id)}
                    disabled={item.lido || marcandoEsteItem}
                  >
                    {marcandoEsteItem ? (
                      <ActivityIndicator size="small" color={colors.oliveGreen} />
                    ) : (
                      <>
                        <Ionicons name="checkmark" size={16} color={item.lido ? colors.textMuted : colors.oliveGreen} />
                        <Text style={[styles.botaoTexto, item.lido && styles.botaoTextoLido]}>
                          {item.lido ? 'Lido' : 'Marcar como lido'}
                        </Text>
                      </>
                    )}
                  </Pressable>
                </View>
              </View>
            );
          }}
        />
      )}

      <ToastSucesso mensagem={mensagemToast} />
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
  logo: { width: 32, height: 32, resizeMode: 'contain' },
  headerTitulo: { color: colors.white, fontSize: 18, fontWeight: '700' },
  filtrosContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 4,
  },
  filtroChip: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#DADAD2',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: colors.white,
  },
  filtroDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  filtroTexto: { fontSize: 13, fontWeight: '600', color: colors.textDark },
  lista: { flex: 1 },
  listaConteudo: { padding: 12, paddingBottom: 24 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    marginBottom: 14,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  faixa: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  faixaEsquerda: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  faixaTexto: { color: colors.white, fontWeight: '700', fontSize: 13 },
  novoBadge: { backgroundColor: colors.novoBadgeBg, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  novoTexto: { color: colors.white, fontSize: 11, fontWeight: '700' },
  corpo: { padding: 14 },
  titulo: { fontSize: 15, fontWeight: '700', color: colors.textDark, marginBottom: 4 },
  descricao: { fontSize: 13, lineHeight: 18, marginBottom: 8 },
  data: { fontSize: 11, color: colors.textMuted, marginBottom: 12 },
  botao: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1.5,
    borderColor: colors.oliveGreen,
    borderRadius: 24,
    paddingVertical: 10,
  },
  botaoLido: { borderColor: '#DADAD2', backgroundColor: '#F2F2ED' },
  botaoTexto: { color: colors.oliveGreen, fontWeight: '700', fontSize: 13 },
  botaoTextoLido: { color: colors.textMuted }
});