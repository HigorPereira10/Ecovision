/**
 * A cor que cada estado da planta recebe na interface, num lugar só.
 *
 * POR QUE ISTO EXISTE
 * -------------------
 * A regra era `saudavel ? verde : vermelho`, escrita à mão em quatro
 * telas. Quando a classe `estresse_foliar` entrou em produção, duas
 * delas foram atualizadas para o vocabulário de três estados e duas
 * não, e o resultado apareceu nas capturas de 06/11/2026: o mesmo
 * diagnóstico saía âmbar no card de situação sanitária do Início e
 * VERMELHO na tela de Diagnóstico e na lista do Histórico.
 *
 * Vermelho é a cor de doença neste app. Pintar estresse de vermelho diz
 * ao produtor exatamente o contrário do que o texto logo abaixo diz, que
 * é "alteração na folha que NÃO corresponde às doenças que o sistema
 * reconhece".
 *
 * Com a decisão num lugar só, a próxima classe nova muda quatro telas de
 * uma vez, ou nenhuma.
 */

import { colors } from './colors';

/** O que a cor precisa saber sobre o diagnóstico.
 *
 * Campos soltos em vez do tipo Diagnostico inteiro, de propósito: assim
 * este módulo fica em theme/ sem depender de services/, e um teste pode
 * passar um objeto literal. */
interface EstadoDoDiagnostico {
  semDiagnostico: boolean;
  saudavel: boolean;
  estresse: boolean;
}

/** Cor do estado da planta.
 *
 * A ordem dos testes importa: `semDiagnostico` vem primeiro porque
 * ausência de resposta não é estado da planta, e as outras duas
 * perguntas não se aplicam a ela.
 *
 * O caso padrão é vermelho, por exclusão e de propósito: classe nova que
 * não seja sadia, estresse nem ausência de diagnóstico é doença, e errar
 * para "avisa demais" é o lado seguro. É a mesma regra de ehDoenca() em
 * src/domain/doencas.ts. */
export function corDoDiagnostico(d: EstadoDoDiagnostico): string {
  if (d.semDiagnostico) return colors.informativo;
  if (d.saudavel) return colors.oliveGreen;
  if (d.estresse) return colors.cuidado;
  return colors.danger;
}
