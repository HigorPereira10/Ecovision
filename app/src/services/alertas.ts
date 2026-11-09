/**
 * Alertas do usuário, a partir de GET /alertas e PATCH /alertas/{id}/lido.
 *
 * A API grava a severidade como 'alta' ou 'media', e a tela usa 'critico',
 * 'cuidado' e 'informativo'; a tradução fica aqui, e valores desconhecidos
 * viram 'informativo'. O alerta sintético de dispositivo inativo chega com
 * id null e sintetico=true: não pode ser marcado como lido, e `chave`
 * fornece um identificador estável para a lista.
 */

import { get, patch } from './api';

/** Vocabulário da TELA. Mantido como estava para não refazer o design. */
export type SeveridadeAlerta = 'critico' | 'cuidado' | 'informativo';

/** Vocabulário do BANCO, traduzido acima. */
const SEVERIDADE_DA_API: Record<string, SeveridadeAlerta> = {
  alta: 'critico',
  media: 'cuidado',
  baixa: 'informativo',
};

/** Formato devolvido pela API (GET /alertas). */
interface AlertaDaApi {
  id: number | null;
  titulo: string;
  descricao: string;
  severidade: string;
  lido: boolean;
  criado_em: string;
  sintetico: boolean;
}

export interface Alerta {
  /** null no alerta sintético de dispositivo inativo. */
  id: number | null;
  /** Identificador estável de lista, inclusive para o item sem id. */
  chave: string;
  titulo: string;
  descricao: string;
  severidade: SeveridadeAlerta;
  lido: boolean;
  /** true = calculado pela API, não existe no banco, não pode ser lido. */
  sintetico: boolean;
  timestamp: string;
}

function traduzir(bruto: AlertaDaApi): Alerta {
  return {
    id: bruto.id,
    // O sintético é sempre no máximo um por resposta, então 'sintetico'
    // basta como chave; os reais usam o id do banco.
    chave: bruto.id !== null ? `alerta-${bruto.id}` : 'alerta-sintetico',
    titulo: bruto.titulo,
    descricao: bruto.descricao,
    severidade: SEVERIDADE_DA_API[bruto.severidade] ?? 'informativo',
    lido: bruto.lido,
    sintetico: bruto.sintetico,
    timestamp: bruto.criado_em,
  };
}

/** Alertas do usuário, do mais recente ao mais antigo; o alerta sintético
 * usa a data da última captura e se posiciona junto com os demais. */
export async function getAlertas(): Promise<Alerta[]> {
  const brutos = await get<AlertaDaApi[]>('/alertas');
  return brutos
    .map(traduzir)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

/** Marca um alerta real como lido. Só aceita alerta com id: chamar isto
 * para o sintético é erro de programação, não condição de rede, por
 * isso falha alto em vez de ir pedir 404 à API. */
export async function marcarAlertaLido(alertaId: number | null): Promise<void> {
  if (alertaId === null) {
    throw new Error('Alerta de dispositivo inativo não pode ser marcado como lido.');
  }
  await patch(`/alertas/${alertaId}/lido`);
}
