/**
 * src/config/env.ts
 *
 * Camada central de acesso às variáveis de ambiente do app.
 * Usa o padrão EXPO_PUBLIC_* (nativo do Metro Bundler), sem depender
 * de bibliotecas externas como react-native-dotenv.
 *
 * ATENÇÃO, O ACESSO PRECISA SER ESTÁTICO: o Metro substitui
 * `process.env.EXPO_PUBLIC_ALGUMA_COISA` pelo valor literal durante o
 * empacotamento. Ele faz isso procurando essa forma exata no código, e
 * NÃO consegue resolver um acesso dinâmico como `process.env[chave]`.
 *
 * Esta é a correção de um bug real: a versão anterior lia
 * `process.env[key]` dentro de uma função. No servidor de
 * desenvolvimento funcionava, porque lá o `process.env` existe de
 * verdade em tempo de execução. Já no app publicado (EAS Update ou
 * APK), nada era substituído, as duas variáveis chegavam `undefined`,
 * e o `throw` abaixo derrubava o app ANTES de desenhar qualquer tela,
 * com um "Something went wrong" sem explicação.
 *
 * Então: nunca transforme as leituras abaixo em acesso por variável,
 * por mais repetitivo que pareça.
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
