/**
 * app/src/services/auth.ts
 *
 * Framework: Expo (React Native), decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Lógica de autenticação do produtor: login, armazenamento seguro do
 * JWT de acesso (24h) e do refresh token (30 dias), e renovação
 * automática (Blueprint Seção 4.3).
 *
 * VERSÃO MOCK: simula POST /auth/login e POST /auth/refresh localmente,
 * sem chamar a API real. Tokens são strings falsas, mas o fluxo
 * (armazenar, renovar, limpar) é o mesmo que será usado depois.
 *
 * TODO: quando cloud/app/api/routes/auth.py estiver pronto, trocar o
 * corpo de login()/refresh() por chamadas reais via app/src/services/api.ts,
 * mantendo as mesmas assinaturas de função (as telas não precisam mudar).
 */

import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "ecovision_access_token";
const REFRESH_TOKEN_KEY = "ecovision_refresh_token";

// Credencial mockada, usar para testar o login enquanto a API não existe.
const USUARIO_MOCK = {
  email: "joao.pereira@exemplo.com",
  senha: "tomate123",
};

function gerarTokenFalso(prefixo: string): string {
  return `${prefixo}.mock.${Date.now()}`;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// --- Notificação de mudança de estado de autenticação ---
// Permite que AppNavigator (ou qualquer outro componente) reaja
// automaticamente a login()/logout(), sem precisar reiniciar o app.
type AuthListener = (autenticado: boolean) => void;
const listeners = new Set<AuthListener>();

function notificarMudancaDeAuth(autenticado: boolean) {
  listeners.forEach((listener) => listener(autenticado));
}

export function subscribeAuthChanges(listener: AuthListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener); // função de cleanup pro useEffect
}

export async function login(email: string, senha: string): Promise<void> {
  await delay(600); // simula latência de rede

  const credenciaisValidas =
    email.trim().toLowerCase() === USUARIO_MOCK.email && senha === USUARIO_MOCK.senha;

  if (!credenciaisValidas) {
    throw new Error("Email ou senha inválidos.");
  }

  const accessToken = gerarTokenFalso("access");
  const refreshToken = gerarTokenFalso("refresh");

  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);

  notificarMudancaDeAuth(true);
}

export async function refresh(): Promise<void> {
  const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);

  if (!refreshToken) {
    notificarMudancaDeAuth(false);
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  await delay(300);
  const novoAccessToken = gerarTokenFalso("access");
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, novoAccessToken);
}

export async function logout(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  notificarMudancaDeAuth(false);
}

export async function isAuthenticated(): Promise<boolean> {
  const token = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  return token !== null;
}

export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}
