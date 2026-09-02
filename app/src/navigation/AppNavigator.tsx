/**
 * app/src/navigation/AppNavigator.tsx
 *
 * Framework: Expo (React Native) — decisão confirmada pelo grupo.
 * Navegação do app (React Navigation): Welcome -> Login -> (Dashboard |
 * Alertas | Diagnóstico | Histórico | Financeiro), com guarda de rota
 * baseada na presença de um JWT válido (app/src/services/auth.ts).
 *
 * VERSÃO MOCK: isAuthenticated() checa o SecureStore local (sem API real).
 * O AppNavigator se inscreve em subscribeAuthChanges() para reagir
 * automaticamente a login()/logout(), trocando de tela sem reload.
 *
 * Alteração desta versão: aba "Historico" passa a usar headerShown:
 * false, igual a Dashboard e Diagnostico, porque a tela agora tem seu
 * próprio header customizado (logo + título). Sem isso, apareciam dois
 * headers sobrepostos (o nativo do Tab.Navigator + o da tela).
 */

import React, { useEffect, useState } from "react";
import { Pressable, Text } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import WelcomeScreen from "../screens/WelcomeScreen";
import LoginScreen from "../screens/LoginScreen";
import DashboardScreen from "../screens/DashboardScreen";
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
      <Tab.Screen name="Alertas" component={AlertasScreen} options={{ headerShown: false }} />
      <Tab.Screen
        name="Diagnostico"
        component={DiagnosticoScreen}
        options={{ headerShown: false, title: 'Diagnóstico' }}
      />
      <Tab.Screen
        name="Historico"
        component={HistoricoScreen}
        options={{ headerShown: false, title: 'Histórico' }}
      />
      <Tab.Screen name="Financeiro" component={FinanceiroScreen} />
      <Tab.Screen name="Dashboard" component={DashboardScreen} options={{ headerShown: false, title: 'Início' }} />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    checkIsAuthenticated().then(setIsAuthenticated);

    const unsubscribe = subscribeAuthChanges((autenticado) => {
      setIsAuthenticated(autenticado);
    });

    return unsubscribe;
  }, []);

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