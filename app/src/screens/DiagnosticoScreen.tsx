/**
 * app/src/screens/DiagnosticoScreen.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Exibe o diagnóstico mais recente (ou um diagnóstico específico),
 * incluindo a foto da folha. A URL da imagem vem PRONTA da API, 
 * esta tela nunca busca a imagem diretamente no Supabase Storage 
 * (Blueprint Seção 4.2, passo 5).
 *
 * Relação com o resto do sistema:
 * - Consome cloud/app/api/routes/historico.py (ou /diagnostico, a depender do endpoint final)
 *   via app/src/services/api.ts.
 */

// import React from "react";
// import { View, Image, Text } from "react-native";
// import { api } from "../services/api";

// export default function DiagnosticoScreen() {
//   // TODO: buscar diagnóstico via api, exibir imagem (URL do Supabase Storage) e resultado
//   throw new Error("Not implemented");
// }
