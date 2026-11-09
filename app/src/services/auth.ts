/**
 * Autenticação do usuário: login, cadastro, confirmação de e-mail,
 * recuperação de senha, logout e renovação de sessão.
 *
 * O armazenamento dos tokens fica em tokens.ts e as chamadas HTTP em
 * api.ts, mantendo as dependências em linha reta (tokens <- api <- auth).
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
/** Resposta de POST /auth/register: `email_verificado` é false quando um
 * código foi enviado e true quando a conta já foi ativada (servidor sem
 * envio de e-mail); a tela decide entre a confirmação e o login. */
export interface ContaCriada {
  id: number;
  nome: string | null;
  email: string;
  email_verificado: boolean;
}

/** Cria a conta do produtor (POST /auth/register).
 *
 * A conta nova não vê dados até vincular um dispositivo, e não há login
 * automático: o e-mail ainda precisa ser confirmado. */
export async function registrar(dados: {
  nome: string;
  email: string;
  senha: string;
}): Promise<ContaCriada> {
  return postSemAutenticacao<ContaCriada>("/auth/register", {
    nome: dados.nome.trim(),
    email: dados.email.trim().toLowerCase(),
    senha: dados.senha,
  });
}

/** Confirma o cadastro com o código de 6 dígitos recebido por e-mail
 * (POST /auth/verify-email). */
export async function verificarEmail(email: string, codigo: string): Promise<void> {
  await postSemAutenticacao("/auth/verify-email", {
    email: email.trim().toLowerCase(),
    codigo: codigo.trim(),
  });
}

/** Pede um novo código de confirmação (POST /auth/resend-code).
 *
 * A API responde sempre da mesma forma, então a tela não pode afirmar que
 * o e-mail foi enviado; por isso o botão mantém uma contagem regressiva. */
export async function reenviarCodigo(email: string): Promise<void> {
  await postSemAutenticacao("/auth/resend-code", {
    email: email.trim().toLowerCase(),
  });
}

/** Pede o código de redefinição de senha (POST /auth/forgot-password).
 *
 * A API responde sempre da mesma forma, exista ou não a conta. */
export async function solicitarRecuperacaoSenha(email: string): Promise<void> {
  await postSemAutenticacao("/auth/forgot-password", {
    email: email.trim().toLowerCase(),
  });
}

/** Troca a senha usando o código recebido por e-mail
 * (POST /auth/reset-password). A nova senha passa pelas mesmas regras
 * de força do cadastro, validadas no servidor. */
export async function redefinirSenha(
  email: string,
  codigo: string,
  novaSenha: string,
): Promise<void> {
  await postSemAutenticacao("/auth/reset-password", {
    email: email.trim().toLowerCase(),
    codigo: codigo.trim(),
    nova_senha: novaSenha,
  });
}
