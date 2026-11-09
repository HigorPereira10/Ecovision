/**
 * Notificações locais de alertas (expo-notifications, sem servidor de push).
 *
 * verificarNovosAlertasNaoLidos() compara os alertas não lidos da API com
 * os já notificados (guardados no AsyncStorage) e notifica apenas os novos.
 * dispararNotificacaoTeste() gera uma notificação de demonstração, exibida
 * só em desenvolvimento ou para administradores.
 *
 * A biblioteca é carregada sob demanda: a partir do SDK 53 ela registra um
 * listener de push ao ser importada, o que lança exceção no Expo Go. Se o
 * carregamento falhar, as funções viram no-op e o app segue normalmente.
 */

import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getAlertas, Alerta, SeveridadeAlerta } from './alertas';
import { colors } from '../theme/colors';

type ModuloNotificacoes = typeof import('expo-notifications');

// Guarda a chave de cada alerta, e não o id numérico, porque o alerta
// sintético de dispositivo inativo chega com id null. O sufixo no nome do
// armazenamento marca a mudança de formato e faz a lista antiga ser
// ignorada.
const CHAVE_IDS_NOTIFICADOS = '@ecovision:notificacoes_chaves_notificadas';

const SEVERIDADE_TITULO: Record<SeveridadeAlerta, string> = {
  critico: '🔴 Alerta crítico',
  cuidado: '🟠 Alerta de atenção',
  informativo: 'ℹ️ Novo alerta',
};

let inicializado = false;
let moduloCarregado: ModuloNotificacoes | null = null;
let carregamentoFalhou = false;

/** Carrega expo-notifications sob demanda. Devolve null (uma única vez,
 * sem repetir a tentativa) se a biblioteca não puder ser usada neste
 * ambiente, para quem chama tratar como "notificação indisponível". */
async function carregarNotificacoes(): Promise<ModuloNotificacoes | null> {
  if (moduloCarregado) return moduloCarregado;
  if (carregamentoFalhou) return null;

  try {
    const modulo = await import('expo-notifications');

    // No Expo Go o import pode concluir com funções ausentes em vez de
    // lançar exceção; a verificação evita um TypeError posterior.
    if (typeof modulo.setNotificationHandler !== 'function') {
      throw new Error('Módulo carregou incompleto (funções ausentes).');
    }

    moduloCarregado = modulo;
    return moduloCarregado;
  } catch (erro) {
    carregamentoFalhou = true;
    console.warn(
      '[notificacoes] expo-notifications indisponível neste ambiente ' +
        '(esperado no Expo Go desde o SDK 53). As notificações ficam ' +
        'desativadas, o resto do app funciona normalmente.',
      erro,
    );
    return null;
  }
}

/**
 * Configura a exibição em primeiro plano e o canal de notificação do
 * Android. Idempotente.
 */
export async function inicializarNotificacoes(): Promise<void> {
  if (inicializado) return;

  const Notifications = await carregarNotificacoes();
  if (!Notifications) return;

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
 * Garante a permissão de notificação, pedindo ao usuário se necessário.
 * Devolve false se foi negada; quem chama deve seguir sem notificar.
 */
async function garantirPermissao(): Promise<boolean> {
  const Notifications = await carregarNotificacoes();
  if (!Notifications) return false;

  const atual = await Notifications.getPermissionsAsync();
  if (atual.status === 'granted') return true;

  const pedida = await Notifications.requestPermissionsAsync();
  return pedida.status === 'granted';
}

/**
 * Dispara uma notificação local imediata representando um alerta.
 */
export async function dispararNotificacaoAlerta(alerta: Alerta): Promise<void> {
  await inicializarNotificacoes();

  const Notifications = await carregarNotificacoes();
  if (!Notifications) return;

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
 * Dispara uma notificação de demonstração, sem depender de alertas reais.
 * Usada pelo botão da tela de Alertas, visível apenas em desenvolvimento
 * ou para administradores.
 */
export async function dispararNotificacaoTeste(): Promise<void> {
  const alertaDemo: Alerta = {
    id: -1,
    chave: 'alerta-demo',
    severidade: 'cuidado',
    titulo: 'Novo alerta fitossanitário detectado na estufa 1',
    descricao: 'Notificação de demonstração (EcoVision).',
    lido: false,
    sintetico: false,
    timestamp: new Date().toISOString(),
  };

  await dispararNotificacaoAlerta(alertaDemo);
}

/**
 * Busca os alertas não lidos e notifica os que ainda não foram notificados
 * nesta instalação. Devolve quantos foram notificados.
 *
 * Chamada ao focar a tela de Alertas: a notificação é disparada pelo
 * aparelho, então não há aviso com o aplicativo fechado.
 */
export async function verificarNovosAlertasNaoLidos(): Promise<number> {
  // Sai antes de tocar no AsyncStorage: sem isso, os alertas seriam
  // marcados como "já notificados" sem notificação nenhuma ter saído, e
  // o produtor nunca mais seria avisado deles num build onde funciona.
  if (!(await carregarNotificacoes())) return 0;

  const alertas = await getAlertas();
  const naoLidos = alertas.filter((a) => !a.lido);
  if (naoLidos.length === 0) return 0;

  const chavesRaw = await AsyncStorage.getItem(CHAVE_IDS_NOTIFICADOS);
  const chavesNotificadas: string[] = chavesRaw ? JSON.parse(chavesRaw) : [];
  const jaNotificadas = new Set(chavesNotificadas);

  const novos = naoLidos.filter((a) => !jaNotificadas.has(a.chave));
  if (novos.length === 0) return 0;

  for (const alerta of novos) {
    await dispararNotificacaoAlerta(alerta);
    jaNotificadas.add(alerta.chave);
  }

  await AsyncStorage.setItem(CHAVE_IDS_NOTIFICADOS, JSON.stringify(Array.from(jaNotificadas)));
  return novos.length;
}