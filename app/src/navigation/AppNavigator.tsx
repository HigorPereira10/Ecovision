/**
 * app/src/navigation/AppNavigator.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Ver docs/decisions/0002-frontend-framework-pendente.md (ADR 0002).
 *
 * Navegação do app (React Navigation, citado no Sumário Executivo do
 * Blueprint v3.0). Define o fluxo: Login -> (Alertas | Diagnóstico |
 * Histórico | Financeiro), com guarda de rota baseada na presença de
 * um JWT válido (app/src/services/auth.ts).
 *
 * Relação com o resto do sistema:
 * - Compõe todas as telas de app/src/screens/.
 */

// import React from "react";
// import { NavigationContainer } from "@react-navigation/native";
// import { createNativeStackNavigator } from "@react-navigation/native-stack";
// import LoginScreen from "../screens/LoginScreen";
// import AlertasScreen from "../screens/AlertasScreen";
// import DiagnosticoScreen from "../screens/DiagnosticoScreen";
// import HistoricoScreen from "../screens/HistoricoScreen";
// import FinanceiroScreen from "../screens/FinanceiroScreen";

// export default function AppNavigator() {
//   // TODO: stack/tab navigator com guarda de autenticação
//   throw new Error("Not implemented");
// }
