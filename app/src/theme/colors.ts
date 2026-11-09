/**
 * Paleta central do EcoVision, extraída do design (logo + telas de
 * carregamento/login). Usada por todas as telas para manter consistência
 * visual sem repetir valores hexadecimais espalhados pelo código.
 */

export const colors = {
  // Verdes (fundo das áreas "institucionais": splash, boas-vindas, topo do login)
  darkGreen: "#152B0B",
  green: "#3F6B1D",
  oliveGreen: "#5B8C2A", // botões primários e links
  lightOlive: "#8CBF4A", // ícones/destaques sobre fundo escuro

  // Neutros (área de formulário)
  cream: "#F5F4EE",
  white: "#FFFFFF",

  // Textos
  textDark: "#1B2E0E",
  textMuted: "#6B7566",
  textOnDark: "#D9E6C9",

  // Estados
  danger: "#C0392B", // também usado como cor de severidade "Crítico"
  cuidado: "#D9A227", // severidade "Cuidado" (âmbar/mostarda)
  informativo: "#8C9086", // severidade "Informativo" (cinza neutro)
  novoBadgeBg: "rgba(255,255,255,0.25)", // fundo do selo "novo" sobre as faixas coloridas

  // Cores de categoria das leituras ambientais (cards do Dashboard)
  laranjaTemperatura: "#D9772E",
  azulUmidade: "#3E7CB8",
};