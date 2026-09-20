/**
 * app/src/services/notificacoes.ts
 *
 * Serviço de notificações locais, usado para simular o alerta que,
 * futuramente, vai ser disparado pelo backend (cloud/) quando um novo
 * diagnóstico gerar um alerta fitossanitário. Hoje é 100% local
 * (expo-notifications, sem push server) — é o diferencial de Fase 5
 * do Blueprint que justifica a escolha do Expo frente às alternativas
 * (React PWA/Streamlit não suportam push nativo).
 *
 * Duas formas de disparo, propositalmente:
 * 1) dispararNotificacaoTeste() — botão manual na tela de Alertas,
 *    útil pra demonstração na banca (não depende de estado dos dados).
 * 2) verificarNovosAlertasNaoLidos() — "automático": compara os
 *    alertas não lidos vindos de services/alertas.ts com os IDs já
 *    notificados (persistidos em AsyncStorage) e dispara notificação
 *    só para os que ainda não foram notificados nesta sessão/instalação.
 *
 * TODO quando o backend/IoT estiverem prontos:
 * - O disparo deixa de ser "polling" local e passa a reagir a um
 *   evento real (push remoto do FastAPI, ou notificação recebida via
 *   addNotificationReceivedListener). A função verificarNovosAlertasNaoLidos()
 *   pode ser removida ou mantida como fallback offline.
 * - Local notifications continuam funcionando no Expo Go; push remoto
 *   exige development build (não usado aqui).
 */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getAlertas, Alerta, SeveridadeAlerta } from './alertas';
import { colors } from '../theme/colors';

const CHAVE_IDS_NOTIFICADOS = '@ecovision:notificacoes_ids_notificados';

const SEVERIDADE_TITULO: Record<SeveridadeAlerta, string> = {
  critico: '🔴 Alerta crítico',
  cuidado: '🟠 Alerta de atenção',
  informativo: 'ℹ️ Novo alerta',
};

let inicializado = false;

/**
 * Configura o comportamento de exibição em primeiro plano e o canal
 * de notificação do Android. Idempotente — pode ser chamada em mais
 * de uma tela sem efeito colateral.
 */
export async function inicializarNotificacoes(): Promise<void> {
  if (inicializado) return;

  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('alertas-fitossanitarios', {
      name: 'Alertas fitossanitários',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: colors.danger,
    });
  }

  inicializado = true;
}

/**
 * Garante que a permissão de notificação foi concedida, pedindo ao
 * usuário se ainda não foi decidido. Retorna false se foi negada —
 * quem chamar deve tratar esse caso silenciosamente (não travar o app).
 */
async function garantirPermissao(): Promise<boolean> {
  const atual = await Notifications.getPermissionsAsync();
  if (atual.status === 'granted') return true;

  const pedida = await Notifications.requestPermissionsAsync();
  return pedida.status === 'granted';
}

/**
 * Dispara uma notificação local imediata representando um alerta.
 * Futuro: quando o backend existir, essa função pode ser chamada a
 * partir de um listener de push (addNotificationReceivedListener) ao
 * invés de ser chamada diretamente pela tela.
 */
export async function dispararNotificacaoAlerta(alerta: Alerta): Promise<void> {
  await inicializarNotificacoes();

  const permitido = await garantirPermissao();
  if (!permitido) return;

  await Notifications.scheduleNotificationAsync({
    content: {
      title: SEVERIDADE_TITULO[alerta.severidade],
      body: alerta.titulo,
      data: { alertaId: alerta.id },
      sound: 'default',
    },
    trigger: null, // dispara imediatamente
  });
}

/**
 * Dispara uma notificação de demonstração, sem depender do estado
 * real dos mocks. Usada pelo botão de teste na tela de Alertas —
 * pensada especificamente pra demonstração na banca.
 */
export async function dispararNotificacaoTeste(): Promise<void> {
  const alertaDemo: Alerta = {
    id: -1,
    tipo: 'demo',
    severidade: 'cuidado',
    titulo: 'Novo alerta fitossanitário detectado na estufa 1',
    descricao: 'Notificação de demonstração (EcoVision).',
    lido: false,
    timestamp: new Date().toISOString(),
  };

  await dispararNotificacaoAlerta(alertaDemo);
}

/**
 * "Verificação automática": busca os alertas não lidos e dispara
 * notificação apenas para os que ainda não foram notificados nesta
 * instalação do app (controle via AsyncStorage). Retorna quantos
 * alertas novos foram notificados.
 *
 * Pensada pra ser chamada ao abrir/focar a tela de Alertas — quando o
 * backend real existir, o ideal é substituir por um listener reativo
 * em vez de checagem sob demanda.
 */
export async function verificarNovosAlertasNaoLidos(): Promise<number> {
  const alertas = await getAlertas();
  const naoLidos = alertas.filter((a) => !a.lido);
  if (naoLidos.length === 0) return 0;

  const idsNotificadosRaw = await AsyncStorage.getItem(CHAVE_IDS_NOTIFICADOS);
  const idsNotificados: number[] = idsNotificadosRaw ? JSON.parse(idsNotificadosRaw) : [];
  const idsNotificadosSet = new Set(idsNotificados);

  const novos = naoLidos.filter((a) => !idsNotificadosSet.has(a.id));
  if (novos.length === 0) return 0;

  for (const alerta of novos) {
    await dispararNotificacaoAlerta(alerta);
    idsNotificadosSet.add(alerta.id);
  }

  await AsyncStorage.setItem(CHAVE_IDS_NOTIFICADOS, JSON.stringify(Array.from(idsNotificadosSet)));
  return novos.length;
}