/**
 * Cliente HTTP da API, com autenticação por JWT. O aplicativo nunca acessa
 * o Supabase diretamente.
 *
 * Usa fetch nativo. Quando a API responde 401 em uma rota autenticada, o
 * cliente renova o token de acesso uma única vez e repete a requisição;
 * se a renovação falhar, faz logout e propaga o erro, e a navegação volta
 * ao login.
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

/** Mensagem de erro da API (campo `detail` do FastAPI), se houver.
 *
 * O `detail` pode ser uma string, uma lista de strings (todas as regras de
 * senha não cumpridas no cadastro) ou uma lista de objetos {loc, msg, type}
 * gerada pelo Pydantic; os três formatos viram texto legível. */
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
 * fetch com tempo limite: o React Native não aplica timeout por padrão.
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
 * Troca o token de renovação guardado por um novo token de acesso. Fica
 * neste módulo para evitar importação circular com auth.ts.
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
 * Requisição autenticada. Em 401, renova a sessão uma única vez e repete,
 * sem tentar de novo se o token renovado também for recusado.
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

/** PATCH autenticado (por exemplo, marcar um alerta como lido), com a mesma
 * renovação automática de sessão. O corpo é opcional. */
export async function patch<T>(caminho: string, corpo?: unknown): Promise<T> {
  if (corpo === undefined) {
    return requisicaoAutenticada<T>(caminho, { method: "PATCH" });
  }
  return requisicaoAutenticada<T>(caminho, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
}

/**
 * POST sem autenticação, para login e renovação de sessão.
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
