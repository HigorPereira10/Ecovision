/**
 * Converte erros da camada de serviço em mensagens em português para o
 * usuário. "Network request failed" (sem conexão) e erros de tempo limite
 * recebem mensagens próprias.
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

    // Mensagens curtas, sem stack trace, foram escritas pelos serviços
    // para o usuário e são exibidas diretamente.
    if (erro.message.length <= 120) return erro.message;
  }

  return mensagemPadrao;
}

export const MENSAGENS_ERRO = {
  SEM_CONEXAO: MENSAGEM_SEM_CONEXAO,
  TIMEOUT: MENSAGEM_TIMEOUT,
  GENERICA: MENSAGEM_GENERICA,
};
