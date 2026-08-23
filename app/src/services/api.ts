/**
 * app/src/services/api.ts
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Cliente HTTP central para consumir a API FastAPI (cloud/), sempre
 * autenticado via JWT do produtor. Regra do Blueprint (Seção 4.2, passo
 * 5): o frontend NUNCA fala diretamente com o Supabase, só com esta API.
 *
 * Responsabilidades quando implementado:
 * - Anexar automaticamente o header Authorization (JWT de acesso) em
 *   toda requisição.
 * - Renovar o token via refresh token quando expirado (ver
 *   app/src/services/auth.ts), de forma transparente às telas.
 * - Apontar para a URL base da API no Railway (variável de ambiente do app).
 *
 * Relação com o resto do sistema:
 * - Usado por todas as telas em app/src/screens/.
 * - Espelha, do lado do cliente, os endpoints de
 *   cloud/app/api/routes/*.py.
 */

// import axios from "axios";

// export const api = axios.create({
//   // TODO: baseURL a partir de variável de ambiente do app
// });

// TODO: interceptor de request (anexar JWT) e de response (renovar via refresh token em 401)
