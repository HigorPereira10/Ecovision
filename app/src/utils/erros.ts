/**
 * app/src/utils/erros.ts
 *
 * Converte erros lançados pela camada de serviço (services/*.ts) em
 * mensagens amigáveis para o produtor, em português. Centralizado aqui
 * para não duplicar essa lógica em cada tela.
 *
 * Hoje os serviços leem de JSON/AsyncStorage local, então praticamente
 * não falham por rede — mas a assinatura Promise/try-catch já está
 * pronta para quando os erros vierem de fetch() real contra o FastAPI
 * (Semana 3 do cronograma). Nesse cenário, o React Native lança um
 * TypeError com a mensagem "Network request failed" quando não há
 * conexão, e é isso que tratamos como "sem conexão" abaixo.
 */

const MENSAGEM_SEM_CONEXAO =
  'Sem conexão com a internet. Verifique sua rede e tente novamente.';

const MENSAGEM_TIMEOUT =
  'A conexão demorou demais para responder. Tente novamente.';

const MENSAGEM_GENERICA =
  'Não foi possível carregar os dados. Tente novamente.';

function pareceErroDeRede(mensagem: string): boolean {
  const m = mensagem.toLowerCase();
  return (
    m.includes('network request failed') ||
    m.includes('failed to fetch') ||
    m.includes('network error') ||
    m.includes('sem conexão')
  );
}

function pareceTimeout(mensagem: string): boolean {
  const m = mensagem.toLowerCase();
  return m.includes('timeout') || m.includes('timed out') || m.includes('abort');
}

/**
 * Traduz qualquer erro capturado num try/catch para uma mensagem
 * pronta para exibir na tela. Erros de validação/negócio lançados
 * explicitamente pelos serviços (ex: "Email ou senha inválidos.",
 * em auth.ts) são exibidos como estão, pois já foram escritos
 * pensando no usuário final.
 */
export function obterMensagemErro(erro: unknown, mensagemPadrao = MENSAGEM_GENERICA): string {
  if (erro instanceof Error && erro.message) {
    if (pareceErroDeRede(erro.message)) return MENSAGEM_SEM_CONEXAO;
    if (pareceTimeout(erro.message)) return MENSAGEM_TIMEOUT;

    // Mensagens curtas (sem stack trace) normalmente foram escritas à
    // mão pelos serviços para o usuário final — essas podem ser
    // exibidas diretamente em vez de cair na mensagem genérica.
    if (erro.message.length <= 120) return erro.message;
  }

  return mensagemPadrao;
}

export const MENSAGENS_ERRO = {
  SEM_CONEXAO: MENSAGEM_SEM_CONEXAO,
  TIMEOUT: MENSAGEM_TIMEOUT,
  GENERICA: MENSAGEM_GENERICA,
};
