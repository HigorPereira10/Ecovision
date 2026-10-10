/**
 * app/src/navigation/AppNavigator.tsx
 *
 * Framework: Expo (React Native), decisão confirmada pelo grupo.
 * Navegação do app (React Navigation): Welcome -> Login -> Cadastro ->
 * (Dashboard | Alertas | Diagnóstico | Histórico | Financeiro | Perfil),
 * com guarda de rota baseada na presença de um JWT válido
 * (app/src/services/auth.ts).
 *
 * isAuthenticated() checa se existe um token guardado no SecureStore
 * (app/src/services/tokens.ts); quem o emite e a API real.
 * O AppNavigator se inscreve em subscribeAuthChanges() para reagir
 * automaticamente a login()/logout(), trocando de tela sem reload.
 *
 * Todas as abas usam headerShown: false porque cada tela desenha seu
 * próprio header customizado (logo + título). Sem isso, aparecem dois
 * headers sobrepostos (o nativo do Tab.Navigator + o da tela).
 */

import React, { useEffect, useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";

import WelcomeScreen from "../screens/WelcomeScreen";
import LoginScreen from "../screens/LoginScreen";
import CadastroScreen from "../screens/CadastroScreen";
import RecuperarSenhaScreen from "../screens/RecuperarSenhaScreen";
import DashboardScreen from "../screens/DashboardScreen";
import AlertasScreen from "../screens/AlertasScreen";
import DiagnosticoScreen from "../screens/DiagnosticoScreen";
import HistoricoScreen from "../screens/HistoricoScreen";
import FinanceiroScreen from "../screens/FinanceiroScreen";
import PerfilScreen from "../screens/PerfilScreen";
import { isAuthenticated as checkIsAuthenticated, subscribeAuthChanges } from "../services/auth";
import { colors } from "../theme/colors";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

// Mapa nome-da-rota -> ícone Ionicons, usado pelo tabBarIcon abaixo.
const ICONES_TAB: Record<string, keyof typeof Ionicons.glyphMap> = {
  Dashboard: "home-outline",
  Alertas: "notifications-outline",
  Diagnostico: "camera-outline",
  Historico: "time-outline",
  Financeiro: "cash-outline",
  Perfil: "person-outline",
};

function AppTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.oliveGreen,
        tabBarInactiveTintColor: colors.informativo,
        tabBarIcon: ({ color, size }) => (
          <Ionicons name={ICONES_TAB[route.name]} size={size} color={color} />
        ),
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} options={{ title: "Início" }} />
      <Tab.Screen name="Alertas" component={AlertasScreen} />
      <Tab.Screen name="Diagnostico" component={DiagnosticoScreen} options={{ title: "Diagnóstico" }} />
      <Tab.Screen name="Historico" component={HistoricoScreen} options={{ title: "Histórico" }} />
      <Tab.Screen name="Financeiro" component={FinanceiroScreen} />
      <Tab.Screen name="Perfil" component={PerfilScreen} />
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
            <Stack.Screen name="Cadastro" component={CadastroScreen} />
            <Stack.Screen name="RecuperarSenha" component={RecuperarSenhaScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
