/**
 * app/src/navigation/AppNavigator.tsx
 * teste
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Navegação do app (React Navigation): Login -> (Alertas | Diagnóstico |
 * Histórico | Financeiro), com guarda de rota baseada na presença de
 * um JWT válido (app/src/services/auth.ts).
 */

import React, { useEffect, useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import LoginScreen from "../screens/LoginScreen";
import AlertasScreen from "../screens/AlertasScreen";
import DiagnosticoScreen from "../screens/DiagnosticoScreen";
import HistoricoScreen from "../screens/HistoricoScreen";
import FinanceiroScreen from "../screens/FinanceiroScreen";

// TODO: trocar por uma função real de src/services/auth.ts
// assim que eu souber o formato exato (ex: getToken(), isAuthenticated()).
async function checkAuthPlaceholder(): Promise<boolean> {
  return false;
}

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function AppTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: true }}>
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
    checkAuthPlaceholder().then(setIsAuthenticated);
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
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}