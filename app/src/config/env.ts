/**
 * Variáveis de ambiente do aplicativo (padrão EXPO_PUBLIC_* do Metro).
 *
 * O acesso precisa ser estático (process.env.EXPO_PUBLIC_NOME): o Metro
 * substitui essa forma exata pelo valor no empacotamento, e um acesso
 * dinâmico como process.env[chave] chega indefinido no app publicado.
 */

// Lidas de forma estática, uma por uma, para o Metro poder substituir.
const API_URL = process.env.EXPO_PUBLIC_API_URL;
const API_TIMEOUT = process.env.EXPO_PUBLIC_API_TIMEOUT;

/** Falha com mensagem explícita em vez de deixar o app seguir com um
 * valor inválido e quebrar mais adiante, num ponto que não diz nada
 * sobre a causa. */
function exigir(valor: string | undefined, nome: string): string {
  if (!valor) {
    throw new Error(
      `[env.ts] Variável de ambiente "${nome}" não definida. ` +
        `Em desenvolvimento, verifique o arquivo app/.env. ` +
        `No app publicado, verifique as variáveis do ambiente correspondente ` +
        `no EAS (eas env:list <ambiente>).`
    );
  }
  return valor;
}

export const env = {
  apiUrl: exigir(API_URL, "EXPO_PUBLIC_API_URL"),
  apiTimeout: Number(exigir(API_TIMEOUT, "EXPO_PUBLIC_API_TIMEOUT")),
};
