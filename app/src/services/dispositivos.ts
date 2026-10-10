/**
 * app/src/services/dispositivos.ts
 *
 * Camada de serviço para os dispositivos IoT cadastrados na propriedade
 * (Blueprint v3.0, entidade `dispositivos`).
 *
 * ESTADO MISTO, de propósito:
 *
 * - vincularDispositivo() já fala com a API real (POST /dispositivos/vincular).
 * - getDispositivos() CONTINUA MOCKADA.
 *
 * O motivo de getDispositivos() ainda não ter sido ligada: o
 * DispositivoCard desenha `campo`, `setor`, `intervalo_captura_min` e os
 * três `limiar_*`, que o GET /dispositivos da API não devolve (ver
 * DispositivoOut em cloud/app/db/schemas.py). Ligar agora quebraria o
 * card. Resolver isso é uma escolha de produto, não um detalhe técnico:
 * ou esses campos viram colunas de verdade no backend, ou saem do card.
 * Fica para o time do app decidir.
 */

import { post } from './api';
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

/** Dispositivo como a API devolve hoje (DispositivoOut em
 * cloud/app/db/schemas.py). Note que é um conjunto de campos MENOR que
 * a interface Dispositivo acima, que a tela de Perfil consome. */
export interface DispositivoDaApi {
  id: number;
  device_id: string;
  nome: string | null;
  status: 'ativo' | 'inativo';
  criado_em: string;
}

/**
 * Vincula um aparelho à conta logada, pelo código de pareamento que vem
 * na etiqueta dele (formato ECO-XXXX-XXXX).
 *
 * É este passo que faz o cadastro aberto ser seguro: qualquer pessoa
 * cria conta, mas só enxerga dados depois de provar a posse física de
 * um equipamento. O código deixa de funcionar assim que o aparelho é
 * vinculado, então ninguém toma o dispositivo de outro.
 *
 * Erros que a API devolve e que valem tratar na tela:
 * - 404: código não existe (provavelmente digitação errada)
 * - 409: aparelho já pertence a outra conta
 */
export async function vincularDispositivo(codigo: string): Promise<DispositivoDaApi> {
  return post<DispositivoDaApi>('/dispositivos/vincular', {
    codigo: codigo.trim().toUpperCase(),
  });
}
