/**
 * app/src/services/dispositivos.ts
 *
 * Camada de serviço para os dispositivos IoT da propriedade
 * (Blueprint v3.0, entidade `dispositivos`).
 *
 * Consome a API real: GET /dispositivos e POST /dispositivos/vincular.
 *
 * A tradução entre o formato da API e a interface que as telas
 * consomem acontece AQUI, e não nas telas, pelo mesmo motivo de
 * leituras.ts: assim o DispositivoCard e a PerfilScreen continuam
 * exatamente como estão. Os dois nomes que divergem são
 * `device_id` -> `identificador` e `criado_em` -> `data_instalacao`.
 */

import { get, post } from './api';

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

/** Formato exato devolvido pela API (DispositivoOut em
 * cloud/app/db/schemas.py). Os campos opcionais são nulos enquanto o
 * dispositivo não for provisionado com esses metadados. */
interface DispositivoDaApi {
  id: number;
  device_id: string;
  nome: string | null;
  status: 'ativo' | 'inativo';
  criado_em: string;
  campo: string | null;
  setor: string | null;
  intervalo_captura_min: number | null;
  limiar_temperatura: number;
  limiar_umidade_ar: number;
  limiar_umidade_solo: number;
}

/** Texto exibido quando o metadado ainda não foi preenchido. Melhor do
 * que um valor inventado, que o produtor leria como verdade. */
const NAO_INFORMADO = 'Não informado';

function converter(bruto: DispositivoDaApi): Dispositivo {
  return {
    id: bruto.id,
    identificador: bruto.device_id,
    // Sem nome cadastrado, mostra o próprio identificador: é o que o
    // produtor tem para reconhecer o aparelho.
    nome: bruto.nome?.trim() || bruto.device_id,
    campo: bruto.campo?.trim() || NAO_INFORMADO,
    setor: bruto.setor?.trim() || NAO_INFORMADO,
    status: bruto.status,
    data_instalacao: bruto.criado_em,
    // 0 em vez de um número plausível: o card mostraria "120 min" como
    // se fosse real, e ninguém saberia que é chute.
    intervalo_captura_min: bruto.intervalo_captura_min ?? 0,
    limiar_temperatura: bruto.limiar_temperatura,
    limiar_umidade_ar: bruto.limiar_umidade_ar,
    limiar_umidade_solo: bruto.limiar_umidade_solo,
  };
}

/** Dispositivos vinculados à conta logada. Lista vazia é o caso normal
 * de quem acabou de se cadastrar e ainda não pareou nenhum aparelho. */
export async function getDispositivos(): Promise<Dispositivo[]> {
  const brutos = await get<DispositivoDaApi[]>('/dispositivos');
  return brutos.map(converter);
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
export async function vincularDispositivo(codigo: string): Promise<Dispositivo> {
  const bruto = await post<DispositivoDaApi>('/dispositivos/vincular', {
    codigo: codigo.trim().toUpperCase(),
  });
  return converter(bruto);
}
