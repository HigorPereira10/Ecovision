/**
 * app/src/services/auth.ts
 *
 * Framework: Expo (React Native), decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Lógica de autenticação do produtor: login, logout e renovação de
 * sessão, contra a API real (POST /auth/login e POST /auth/refresh,
 * ver cloud/app/api/routes/auth.py).
 *
 * As assinaturas das funções são as mesmas da versão mock anterior,
 * então nenhuma tela precisou mudar (AppNavigator, LoginScreen e
 * PerfilScreen seguem importando daqui).
 *
 * O armazenamento dos tokens fica em tokens.ts e as chamadas HTTP em
 * api.ts: este módulo só amarra os dois. Essa separação existe para as
 * dependências ficarem em linha reta (tokens <- api <- auth) em vez de
 * circular, já que o cliente HTTP também precisa ler o token e renovar
 * a sessão sozinho ao receber um 401.
 */

import { postSemAutenticacao, renovarSessao } from "./api";
import {
  limparTokens,
  notificarMudancaDeAuth,
  salvarAccessToken,
  salvarRefreshToken,
} from "./tokens";

export { isAuthenticated, getAccessToken, subscribeAuthChanges } from "./tokens";

interface RespostaToken {
  access_token: string;
  refresh_token?: string | null;
  token_type?: string;
}

export async function login(email: string, senha: string): Promise<void> {
  const resposta = await postSemAutenticacao<RespostaToken>("/auth/login", {
    email: email.trim().toLowerCase(),
    senha,
  });

  await salvarAccessToken(resposta.access_token);
  if (resposta.refresh_token) {
    await salvarRefreshToken(resposta.refresh_token);
  }

  notificarMudancaDeAuth(true);
}

/** Troca o refresh token por um access token novo. O cliente HTTP faz
 * isso sozinho ao receber 401; esta função existe para quem precisar
 * renovar de forma explícita. */
export async function refresh(): Promise<void> {
  await renovarSessao();
}

export async function logout(): Promise<void> {
  await limparTokens();
  notificarMudancaDeAuth(false);
}
