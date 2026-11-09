/**
 * Dispositivos do usuário: GET /dispositivos e POST /dispositivos/vincular.
 *
 * Converte `device_id` em `identificador` e `criado_em` em
 * `data_instalacao`, os nomes usados pelas telas.
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
  /** null enquanto o dispositivo não for provisionado com esse
   * metadado. A tela mostra "Não informado", como faz com campo e
   * setor. */
  intervalo_captura_min: number | null;
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
    // Nulo é mantido: exibir "0 min" seria uma informação errada; o card
    // decide como mostrar a ausência.
    intervalo_captura_min: bruto.intervalo_captura_min,
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
 * Vincula um aparelho à conta pelo código de pareamento da etiqueta
 * (ECO-XXXX-XXXX). O código deixa de valer após o vínculo.
 *
 * Erros tratados pela tela:
 * - 404: código inexistente;
 * - 409: aparelho já vinculado a outra conta.
 */
export async function vincularDispositivo(codigo: string): Promise<Dispositivo> {
  const bruto = await post<DispositivoDaApi>('/dispositivos/vincular', {
    codigo: codigo.trim().toUpperCase(),
  });
  return converter(bruto);
}
