/**
 * app/src/services/dispositivos.ts
 *
 * Camada de serviço para os dispositivos IoT cadastrados na propriedade
 * (Blueprint v3.0, entidade `dispositivos`).
 *
 * VERSÃO MOCK: lê de src/mocks/dispositivos.json. Quando o endpoint do
 * Higor estiver pronto (ex: GET /dispositivos), só o corpo desta função
 * muda para um fetch() — a assinatura e o tipo de retorno continuam os
 * mesmos, então a PerfilScreen não precisa ser tocada.
 */

import dispositivosMock from '../mocks/dispositivos.json';

export interface Dispositivo {
  id: number;
  identificador: string;
  nome: string;
  campo: string;
  setor: string;
  status: 'ativo' | 'inativo';
  data_instalacao: string;
  intervalo_captura_min: number;
  limiar_temperatura: number;
  limiar_umidade_ar: number;
  limiar_umidade_solo: number;
}

// Flag de teste: mude pra `true` pra simular falha de rede sem deixar
// um throw solto que possa disparar sozinho na apresentação da banca.
const SIMULAR_ERRO = false;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getDispositivos(): Promise<Dispositivo[]> {
  await delay(500);

  if (SIMULAR_ERRO) {
    throw new Error('Não foi possível carregar os dispositivos.');
  }

  return dispositivosMock as Dispositivo[];
}