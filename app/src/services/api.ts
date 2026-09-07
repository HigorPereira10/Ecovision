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
 * VERSÃO MOCK: ainda não existe requisição HTTP real. Este arquivo por
 * enquanto só expõe o estado de autenticação (via auth.ts) para telas
 * que precisem checar se o produtor está logado (ex.: AppNavigator).
 * As telas de dados (Alertas, Diagnóstico, Histórico) seguem importando
 * os JSONs de src/mocks/ diretamente por enquanto.
 *
 * TODO quando a API estiver pronta:
 * - Criar instância axios com baseURL vindo de variável de ambiente do app.
 * - Interceptor de request: anexar Authorization: Bearer <accessToken>
 *   (usar getAccessToken() de auth.ts).
 * - Interceptor de response: em 401, chamar refresh() de auth.ts e
 *   repetir a requisição original; se refresh falhar, chamar logout()
 *   e redirecionar para LoginScreen.
 * - Migrar as telas para chamar funções deste arquivo (ex.: getAlertas())
 *   em vez de importar os JSONs diretamente.
 */

// import axios from "axios";

export { isAuthenticated, getAccessToken } from "./auth";

// export const api = axios.create({
//   // TODO: baseURL a partir de variável de ambiente do app
// });

// TODO: interceptor de request (anexar JWT) e de response (renovar via refresh token em 401)