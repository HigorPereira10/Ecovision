/**
 * app/src/screens/LoginScreen.tsx
 *
 * ATENÇÃO: escrito sob a estrutura placeholder Expo/React Native, 
 * a decisão de framework de frontend AINDA ESTÁ PENDENTE. 
 * Ver app/README.md e docs/decisions/0002-frontend-framework-pendente.md.
 *
 * Tela de login do produtor, consumindo POST /auth/login
 * (cloud/app/api/routes/auth.py). Ao autenticar com sucesso, deve
 * armazenar o JWT de acesso e o refresh token (ver app/src/services/auth.ts)
 * para uso nas demais telas.
 *
 * Relação com o resto do sistema:
 * - Depende de app/src/services/auth.ts para a chamada HTTP.
 * - É a tela inicial do fluxo de navegação (app/src/navigation/AppNavigator.tsx).
 */

// import React from "react";
// import { View, TextInput, Button } from "react-native";
// import { login } from "../services/auth";

// export default function LoginScreen() {
//   // TODO: formulário de email/senha, chamada a login(), navegação em caso de sucesso
//   throw new Error("Not implemented");
// }
