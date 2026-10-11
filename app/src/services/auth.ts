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
/** Resposta de POST /auth/register. `email_verificado` vem false
 * quando um código de confirmação foi enviado, e true quando o servidor
 * está sem e-mail configurado e já ativou a conta. A tela usa isso para
 * decidir se leva o produtor para a tela de código ou direto ao login. */
export interface ContaCriada {
  id: number;
  nome: string | null;
  email: string;
  email_verificado: boolean;
}

/** Cria a conta do produtor (POST /auth/register).
 *
 * O cadastro é aberto: qualquer pessoa pode criar conta. Isso só é
 * seguro porque a API filtra tudo por dono, então uma conta nova não
 * enxerga nada até vincular um dispositivo pelo código de pareamento
 * que vem com o aparelho (ver vincularDispositivo em dispositivos.ts).
 *
 * Não faz login automático: o e-mail ainda precisa ser confirmado. */
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

/** Pede um código de confirmação novo (POST /auth/resend-code).
 *
 * A API responde sempre a mesma coisa: conta inexistente, conta já
 * confirmada e pedido feito antes do intervalo mínimo de 60 segundos
 * recebem resposta idêntica. Então esta função não tem como dizer à
 * tela se o e-mail saiu de verdade, e a tela não deve prometer que
 * saiu. É por isso que a tela de confirmação mantém o botão em
 * contagem regressiva em vez de confiar na resposta: o cadastro já
 * conta como primeiro envio, e um toque imediato não manda nada. */
export async function reenviarCodigo(email: string): Promise<void> {
  await postSemAutenticacao("/auth/resend-code", {
    email: email.trim().toLowerCase(),
  });
}

/** Pede o código de redefinição de senha (POST /auth/forgot-password).
 *
 * A API responde sempre a mesma coisa, exista ou não a conta, para não
 * entregar quais e-mails estão cadastrados. Por isso esta função não
 * tem como dizer à tela se o endereço existe, e a tela não deve
 * prometer que o e-mail foi enviado, só que ele SERÁ se houver conta. */
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
