/**
 * app/src/services/perfil.ts
 *
 * Camada de serviço para os dados de perfil do produtor logado
 * (nome, email). Separado de auth.ts propositalmente: auth.ts cuida
 * só de token/sessão, este arquivo cuida dos dados de exibição do
 * usuário — mesma separação de responsabilidades usada em
 * leituras.ts / diagnosticos.ts / alertas.ts / gastos.ts.
 *
 * VERSÃO MOCK: retorna um usuário fixo. Quando o backend do Higor
 * tiver um endpoint tipo GET /usuarios/me (autenticado via JWT), essa
 * função passa a fazer esse fetch, mantendo a mesma assinatura.
 */

export interface PerfilUsuario {
  nome: string;
  email: string;
}

const PERFIL_MOCK: PerfilUsuario = {
  nome: 'Amanda Camille',
  email: 'produtor@ecovision.app',
};

const SIMULAR_ERRO = false;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getPerfilUsuario(): Promise<PerfilUsuario> {
  await delay(400);

  if (SIMULAR_ERRO) {
    throw new Error('Não foi possível carregar os dados do perfil.');
  }

  return PERFIL_MOCK;
}