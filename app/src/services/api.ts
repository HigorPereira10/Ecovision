/**
 * app/src/services/api.ts
 *
 * Framework: Expo (React Native), decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Cliente HTTP central para consumir a API FastAPI (cloud/), sempre
 * autenticado via JWT do produtor. Regra do Blueprint (Seção 4.2, passo
 * 5): o frontend NUNCA fala diretamente com o Supabase, só com esta API.
 *
 * Usa fetch nativo em vez de axios de propósito: o axios não está nas
 * dependências, e as mensagens de erro do fetch já são as que
 * src/utils/erros.ts traduz ("Network request failed", "Failed to
 * fetch", abort por timeout).
 *
 * Renovação automática de sessão: quando a API responde 401 num
 * endpoint autenticado, este módulo tenta renovar o access token uma
 * única vez e repete a requisição original. Se a renovação também
 * falhar, faz logout e propaga o erro, e o AppNavigator reage à
 * mudança de estado levando o produtor de volta ao login.
 */

import { env } from "../config/env";
import {
  getAccessToken,
  getRefreshToken,
  limparTokens,
  notificarMudancaDeAuth,
  salvarAccessToken,
} from "./tokens";

export { isAuthenticated, getAccessToken } from "./tokens";

/** Erro com o status HTTP preservado, para quem chama poder reagir ao código. */
export class ErroHttp extends Error {
  constructor(
    public readonly status: number,
    mensagem: string,
  ) {
    super(mensagem);
    this.name = "ErroHttp";
  }
}

/** Mensagem de erro vinda da API (campo `detail` do FastAPI), se houver.
 *
 * O `detail` chega em três formatos diferentes, e todos precisam virar
 * texto legível:
 * - string: a maioria dos erros da nossa API ("Email ou senha inválidos.")
 * - lista de strings: POST /auth/register devolve TODAS as regras de
 *   senha que falharam de uma vez, para a tela marcar o checklist inteiro
 * - lista de objetos {loc, msg, type}: formato automático do Pydantic
 *   quando o corpo da requisição nem chega a ser válido
 *
 * Sem tratar os dois últimos, o usuário veria "A API respondeu com erro
 * 422" sem saber o que corrigir. */
async function extrairMensagemDeErro(resposta: Response): Promise<string> {
  try {
    const corpo = await resposta.json();
    const detalhe = corpo?.detail;

    if (typeof detalhe === "string") return detalhe;

    if (Array.isArray(detalhe) && detalhe.length > 0) {
      const linhas = detalhe
        .map((item) => (typeof item === "string" ? item : item?.msg))
        .filter((item): item is string => typeof item === "string" && item.length > 0);
      if (linhas.length > 0) return linhas.join("\n");
    }
  } catch {
    // corpo vazio ou não-JSON: cai na mensagem genérica abaixo
  }
  return `A API respondeu com erro ${resposta.status}.`;
}

/**
 * fetch com timeout. O React Native não aplica timeout por padrão, então
 * sem isso uma rede instável na estufa deixaria a tela carregando para
 * sempre em vez de mostrar erro.
 */
async function fetchComTimeout(url: string, init: RequestInit): Promise<Response> {
  const controlador = new AbortController();
  const timer = setTimeout(() => controlador.abort(), env.apiTimeout);
  try {
    return await fetch(url, { ...init, signal: controlador.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function enviar(caminho: string, init: RequestInit, comToken: boolean): Promise<Response> {
  const cabecalhos: Record<string, string> = {
    Accept: "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };

  if (comToken) {
    const token = await getAccessToken();
    if (token) cabecalhos.Authorization = `Bearer ${token}`;
  }

  return fetchComTimeout(`${env.apiUrl}${caminho}`, { ...init, headers: cabecalhos });
}

/**
 * Troca o refresh token guardado por um access token novo.
 *
 * Mora aqui, e não em auth.ts, porque é o cliente HTTP que precisa
 * dela para se recuperar sozinho de um 401. Deixá-la em auth.ts criaria
 * um ciclo de importação entre os dois módulos.
 */
export async function renovarSessao(): Promise<void> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) {
    notificarMudancaDeAuth(false);
    throw new ErroHttp(401, "Sessão expirada. Faça login novamente.");
  }

  // POST /auth/refresh devolve só um access token novo: a sessão de 30
  // dias segue contada a partir do login original, então o refresh
  // token guardado não é substituído.
  const resposta = await postSemAutenticacao<{ access_token: string }>("/auth/refresh", {
    refresh_token: refreshToken,
  });

  await salvarAccessToken(resposta.access_token);
}

async function encerrarSessao(): Promise<void> {
  await limparTokens();
  notificarMudancaDeAuth(false);
}

/**
 * Requisição autenticada. Em 401, renova a sessão uma vez e repete.
 * Não repete mais de uma vez de propósito: se o token recém-renovado
 * também for recusado, insistir viraria laço infinito contra a API.
 */
async function requisicaoAutenticada<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  let resposta = await enviar(caminho, init, true);

  if (resposta.status === 401) {
    try {
      await renovarSessao();
    } catch {
      await encerrarSessao();
      throw new ErroHttp(401, "Sessão expirada. Faça login novamente.");
    }
    resposta = await enviar(caminho, init, true);

    if (resposta.status === 401) {
      await encerrarSessao();
      throw new ErroHttp(401, "Sessão expirada. Faça login novamente.");
    }
  }

  if (!resposta.ok) {
    throw new ErroHttp(resposta.status, await extrairMensagemDeErro(resposta));
  }

  return (await resposta.json()) as T;
}

/** GET autenticado. Usado pelos serviços de dados (leituras, diagnósticos, ...). */
export async function get<T>(caminho: string): Promise<T> {
  return requisicaoAutenticada<T>(caminho, { method: "GET" });
}

/** POST autenticado, para ações do produtor logado (vincular um
 * dispositivo, marcar alerta como lido, ...). Passa pelo mesmo caminho
 * do GET, então herda a renovação automática de sessão no 401. */
export async function post<T>(caminho: string, corpo: unknown): Promise<T> {
  return requisicaoAutenticada<T>(caminho, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
}

/**
 * POST sem autenticação, para os endpoints de login e refresh (que são
 * justamente os que ainda não têm token válido para enviar).
 */
export async function postSemAutenticacao<T>(caminho: string, corpo: unknown): Promise<T> {
  const resposta = await enviar(
    caminho,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    },
    false,
  );

  if (!resposta.ok) {
    throw new ErroHttp(resposta.status, await extrairMensagemDeErro(resposta));
  }

  return (await resposta.json()) as T;
}
