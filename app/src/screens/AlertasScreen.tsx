/**
 * app/src/screens/AlertasScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Lista os alertas do produtor autenticado (GET /alertas) e permite
 * marcá-los como lidos (PATCH /alertas/{id}/lido), RBAC do Blueprint
 * Seção 4.3 limita o produtor a essa escrita, não à criação de alertas.
 *
 * Relação com o resto do sistema:
 * - Consome cloud/app/api/routes/alertas.py via app/src/services/api.ts.
 * - Se push notifications estiverem habilitadas (Expo Notifications),
 *   deve reagir a notificações que abrem diretamente nesta tela.
 */

// import React from "react";
// import { FlatList } from "react-native";
// import { api } from "../services/api";

// export default function AlertasScreen() {
//   // TODO: buscar alertas via api, listar, permitir marcar como lido
//   throw new Error("Not implemented");
// }
