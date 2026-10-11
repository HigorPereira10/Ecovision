/**
 * app/src/services/alertas.ts
 *
 * Camada de dados do painel de Alertas. Consome GET /alertas e
 * PATCH /alertas/{id}/lido da API real (ver
 * cloud/app/api/routes/alertas.py).
 *
 * Até 2026-10-11 este módulo lia de src/mocks/alertas.json e guardava o
 * estado "lido" num array em memória, que se perdia a cada reinício do
 * app. Agora o backend é a fonte da verdade: o PATCH persiste no
 * Postgres e vale em qualquer aparelho que entre na mesma conta.
 *
 * DUAS COISAS AQUI NÃO SÃO ÓBVIAS, E AS DUAS QUEBRAM A TELA SE FOREM
 * IGNORADAS:
 *
 * 1. SEVERIDADE TEM VOCABULÁRIO DIFERENTE NAS DUAS PONTAS. O backend
 *    grava 'alta' e 'media' (ver cloud/app/core/alertas_ambientais.py e
 *    o catálogo de cloud/app/core/inference.py); a tela foi construída
 *    com 'critico', 'cuidado' e 'informativo', que é o vocabulário do
 *    design da Amanda. A tela indexa um Record por esse valor, então
 *    uma severidade desconhecida viraria `undefined` e a tela quebraria
 *    ao ler a cor. A tradução acontece aqui, e o `default` do mapa é o
 *    que garante que uma severidade nova inventada no backend degrade
 *    para 'informativo' em vez de derrubar a lista.
 *
 * 2. ALERTA SINTÉTICO NÃO TEM id. O item de "dispositivo inativo" (ADR
 *    0008) é calculado a cada requisição e não existe na tabela
 *    `alertas`: ele chega com id=null e sintetico=true. Não dá para
 *    marcá-lo como lido, porque não há linha para atualizar, e o
 *    backend responde 404 a quem tentar. A tela usa `sintetico` para
 *    esconder o botão, e `chave` para ter um identificador estável de
 *    lista mesmo sem id.
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

/** Alertas do produtor logado, do mais recente para o mais antigo.
 *
 * O alerta sintético de dispositivo inativo, quando existe, vem
 * primeiro da API. A ordenação por data é aplicada depois de propósito
 * apenas sobre a data: o sintético carrega a data da última captura,
 * então ele se posiciona no tempo junto com o resto, sem precisar de
 * tratamento especial. */
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
