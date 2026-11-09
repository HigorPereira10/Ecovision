/**
 * Guarda os tokens de sessão do produtor e avisa quem estiver ouvindo
 * quando o estado de autenticação muda.
 *
 * Existe como módulo separado para quebrar um ciclo de importação: o
 * cliente HTTP (api.ts) precisa ler o token para assinar as
 * requisições, e o serviço de autenticação (auth.ts) precisa do cliente
 * HTTP para fazer login. Com o armazenamento aqui, a dependência fica
 * em linha reta (tokens <- api <- auth) em vez de circular. Ciclo de
 * importação é tolerado pelo Metro, mas pode deixar valores não
 * inicializados dependendo da ordem de carga.
 *
 * Os tokens ficam no SecureStore (Keychain no iOS, Keystore no
 * Android), não em AsyncStorage: são credenciais de sessão, e o
 * AsyncStorage é legível por qualquer processo com acesso ao sandbox
 * do app.
 */

import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "ecovision_access_token";
const REFRESH_TOKEN_KEY = "ecovision_refresh_token";

// Permite que o AppNavigator (ou qualquer componente) reaja a
// login/logout automaticamente, sem precisar reiniciar o app.
type AuthListener = (autenticado: boolean) => void;
const listeners = new Set<AuthListener>();

export function notificarMudancaDeAuth(autenticado: boolean): void {
  listeners.forEach((listener) => listener(autenticado));
}

export function subscribeAuthChanges(listener: AuthListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener); // função de cleanup pro useEffect
}

export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function salvarAccessToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

export async function salvarRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
}

export async function limparTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

export async function isAuthenticated(): Promise<boolean> {
  return (await getAccessToken()) !== null;
}
