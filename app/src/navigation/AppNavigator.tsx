/**
 * Navegação do aplicativo (React Navigation): Welcome, Login e Cadastro,
 * depois as abas Dashboard, Alertas, Diagnóstico, Histórico, Financeiro e
 * Perfil, com guarda de rota baseada no token guardado
 * (src/services/tokens.ts). A tela reage a login e logout por
 * subscribeAuthChanges().
 *
 * VincularDispositivo é empilhada sobre as abas e acessada pelo Perfil; o
 * vínculo não é obrigatório, já que o módulo financeiro funciona sem
 * dispositivo. As abas usam headerShown: false porque cada tela desenha o
 * próprio cabeçalho.
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
import VerificarEmailScreen from "../screens/VerificarEmailScreen";
import VincularDispositivoScreen from "../screens/VincularDispositivoScreen";
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
          <>
            <Stack.Screen name="AppTabs" component={AppTabs} />
            {/* Empilhada sobre as abas, e nao como aba propria: vincular
                aparelho e uma acao pontual, nao um lugar onde o produtor
                volta sempre. A entrada e pelo Perfil. */}
            <Stack.Screen
              name="VincularDispositivo"
              component={VincularDispositivoScreen}
            />
          </>
        ) : (
          <>
            <Stack.Screen name="Welcome" component={WelcomeScreen} />
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Cadastro" component={CadastroScreen} />
            <Stack.Screen name="RecuperarSenha" component={RecuperarSenhaScreen} />
            {/* Confirmacao do cadastro por codigo de e-mail. Fica no
                ramo nao autenticado porque o login e recusado ate o
                e-mail ser confirmado. */}
            <Stack.Screen name="VerificarEmail" component={VerificarEmailScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
