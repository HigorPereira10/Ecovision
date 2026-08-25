/**
 * app/src/navigation/AppNavigator.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Navegação do app (React Navigation): Welcome -> Login -> (Alertas |
 * Diagnóstico | Histórico | Financeiro), com guarda de rota baseada na
 * presença de um JWT válido (app/src/services/auth.ts).
 *
 * VERSÃO MOCK: isAuthenticated() checa o SecureStore local (sem API real).
 * O AppNavigator se inscreve em subscribeAuthChanges() para reagir
 * automaticamente a login()/logout(), trocando de tela sem reload.
 *
 * Alteração desta versão: adicionada WelcomeScreen como rota inicial do
 * stack de não-autenticado (tela de apresentação antes do login).
 */

import React, { useEffect, useState } from "react";
import { Pressable, Text } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import WelcomeScreen from "../screens/WelcomeScreen";
import LoginScreen from "../screens/LoginScreen";
import AlertasScreen from "../screens/AlertasScreen";
import DiagnosticoScreen from "../screens/DiagnosticoScreen";
import HistoricoScreen from "../screens/HistoricoScreen";
import FinanceiroScreen from "../screens/FinanceiroScreen";
import { isAuthenticated as checkIsAuthenticated, subscribeAuthChanges, logout } from "../services/auth";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function BotaoLogout() {
  return (
    <Pressable onPress={() => logout()} style={{ marginRight: 16 }}>
      <Text style={{ color: "#E53935", fontWeight: "bold" }}>Sair</Text>
    </Pressable>
  );
}

function AppTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: true,
        headerRight: () => <BotaoLogout />,
      }}
    >
      <Tab.Screen name="Alertas" component={AlertasScreen} />
      <Tab.Screen name="Diagnostico" component={DiagnosticoScreen} />
      <Tab.Screen name="Historico" component={HistoricoScreen} />
      <Tab.Screen name="Financeiro" component={FinanceiroScreen} />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    // checagem inicial (ex: usuário já tinha logado antes e fechou o app)
    checkIsAuthenticated().then(setIsAuthenticated);

    // escuta mudanças disparadas por login()/logout() em qualquer tela
    const unsubscribe = subscribeAuthChanges((autenticado) => {
      setIsAuthenticated(autenticado);
    });

    return unsubscribe;
  }, []);

  // ainda não sabemos se está logado -> não renderiza nada por enquanto
  if (isAuthenticated === null) {
    return null;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <Stack.Screen name="AppTabs" component={AppTabs} />
        ) : (
          <>
            <Stack.Screen name="Welcome" component={WelcomeScreen} />
            <Stack.Screen name="Login" component={LoginScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
