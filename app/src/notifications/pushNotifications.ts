/**
 * app/src/notifications/pushNotifications.ts
 *
 * ATENÇÃO: escrito sob a estrutura placeholder Expo/React Native, 
 * a decisão de framework de frontend AINDA ESTÁ PENDENTE. 
 * Ver app/README.md e docs/decisions/0002-frontend-framework-pendente.md.
 *
 * Push notifications nativas via Expo Notifications, um dos
 * diferenciais citados no comparativo do Blueprint (Fase 5) a favor de
 * Expo em relação a React PWA/Streamlit (nenhuma das outras duas opções
 * suporta push nativo). Se a decisão final não for Expo, este módulo
 * não tem equivalente direto e a funcionalidade de notificação deve ser
 * reavaliada.
 *
 * Responsabilidades quando implementado:
 * - Registrar o dispositivo para push notifications e obter o token.
 * - Enviar o token para a API (endpoint ainda não definido no Blueprint
 *   — TODO de grupo) para associar ao produtor autenticado.
 * - Tratar o recebimento de notificações (ex.: novo alerta gerado por
 *   um diagnóstico) e navegar para AlertasScreen.
 *
 * Relação com o resto do sistema:
 * - Notificações são disparadas, em última instância, pelo backend
 *   (cloud/) quando um diagnóstico gera um alerta, mecanismo de envio
 *   do lado do servidor ainda não está definido no Blueprint v3.0 (TODO).
 */

// import * as Notifications from "expo-notifications";

// export async function registrarParaPushNotifications(): Promise<string | null> {
//   throw new Error("Not implemented");
// }
