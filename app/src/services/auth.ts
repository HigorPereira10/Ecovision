/**
 * app/src/services/auth.ts
 *
 * ATENÇÃO: escrito sob a estrutura placeholder Expo/React Native, 
 * a decisão de framework de frontend AINDA ESTÁ PENDENTE. 
 * Ver app/README.md e docs/decisions/0002-frontend-framework-pendente.md.
 *
 * Lógica de autenticação do produtor: login, armazenamento seguro do
 * JWT de acesso (24h) e do refresh token (30 dias), e renovação
 * automática (Blueprint Seção 4.3).
 *
 * Responsabilidades quando implementado:
 * - login(email, senha): chama POST /auth/login, guarda os tokens
 *   (ex.: Expo SecureStore, se Expo for a escolha final).
 * - refresh(): chama POST /auth/refresh quando o access token expira.
 * - logout(): limpa os tokens armazenados localmente.
 *
 * Relação com o resto do sistema:
 * - Consumido por app/src/screens/LoginScreen.tsx e por
 *   app/src/services/api.ts (interceptor de renovação).
 * - Espelha cloud/app/api/routes/auth.py.
 */

// export async function login(email: string, senha: string): Promise<void> {
//   throw new Error("Not implemented");
// }

// export async function refresh(): Promise<void> {
//   throw new Error("Not implemented");
// }

// export async function logout(): Promise<void> {
//   throw new Error("Not implemented");
// }
