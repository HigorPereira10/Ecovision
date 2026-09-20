/**
 * src/config/env.ts
 *
 * Camada central de acesso às variáveis de ambiente do app.
 * Usa o padrão EXPO_PUBLIC_* (nativo do Metro Bundler), sem depender
 * de bibliotecas externas como react-native-dotenv.
 *
 * Lança erro explícito em vez de falhar silenciosamente caso a
 * variável não esteja definida.
 */

function readEnvVar(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(
      `[env.ts] Variável de ambiente "${key}" não definida. Verifique o arquivo .env na raiz do projeto.`
    );
  }
  return value;
}

export const env = {
  apiUrl: readEnvVar("EXPO_PUBLIC_API_URL"),
  apiTimeout: Number(readEnvVar("EXPO_PUBLIC_API_TIMEOUT")),
};