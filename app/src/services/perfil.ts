/**
 * app/src/services/perfil.ts
 *
 * Camada de serviço para os dados de perfil do produtor logado.
 * Separado de auth.ts propositalmente: auth.ts cuida só de
 * token/sessão, este arquivo cuida dos dados de exibição do usuário,
 * mesma separação usada em leituras.ts / diagnosticos.ts / alertas.ts.
 *
 * Consome GET /usuarios/me (cloud/app/api/routes/usuarios.py),
 * autenticado pelo JWT que api.ts anexa sozinho.
 */

import { get } from './api';

/** Formato exato devolvido pela API (ver UsuarioOut em
 * cloud/app/db/schemas.py). `nome` vem nulo nas contas semeadas à mão
 * antes da migration 0004 ter criado a coluna. */
interface PerfilDaApi {
  nome: string | null;
  email: string;
  papel: string;
}

export interface PerfilUsuario {
  nome: string;
  email: string;
  papel: string;
}

/** Papel com acesso irrestrito, usado pelo app para decidir o que
 * exibir. Mesmo valor de PAPEL_IRRESTRITO em cloud/app/api/escopo.py. */
export const PAPEL_ADMINISTRADOR = 'administrador';

export async function getPerfilUsuario(): Promise<PerfilUsuario> {
  const dados = await get<PerfilDaApi>('/usuarios/me');

  return {
    // A tela de Perfil desenha o nome em destaque, então um nulo
    // deixaria um espaço em branco sem explicação. Cai para o trecho
    // antes do "@" do e-mail, que é o que a conta tem de mais próximo
    // de um nome. Contas criadas pelo cadastro sempre têm nome.
    nome: dados.nome?.trim() || dados.email.split('@')[0],
    email: dados.email,
    papel: dados.papel,
  };
}
