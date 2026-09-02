/**
 * app/src/services/diagnosticos.ts
 *
 * Camada de dados para diagnósticos de IA. Hoje lê dos mocks locais
 * (src/mocks/diagnosticos.json e src/mocks/imagens.json); no futuro
 * vira fetch() para o FastAPI (GET /diagnosticos). Mesma assinatura
 * async/Promise usada em services/leituras.ts, pra troca sem refatorar
 * a tela.
 */

import diagnosticosMock from '../mocks/diagnosticos.json';
import imagensMock from '../mocks/imagens.json';

export interface RegistroImagem {
  id: number;
  dispositivo_id?: number;
  caminho_arquivo: string;
  resolucao?: string;
  timestamp?: string;
}

export interface Diagnostico {
  id: number;
  registro_imagem_id: number;
  classificacao: string;
  confianca: number;
  recomendacao: string;
  timestamp: string;
}

// TODO: hoje o Blueprint só prevê 1 dispositivo mockado ("ativo"), e
// diagnosticos.json não carrega dispositivo_id (só chega via
// registros_imagem). Enquanto isso não for confirmado, tratamos todo
// diagnóstico como pertencente a este único dispositivo. Ajustar assim
// que registros_imagem trouxer o vínculo real.
const DISPOSITIVO_UNICO_ID = 1;

export async function getDiagnosticos(): Promise<Diagnostico[]> {
  const lista = [...(diagnosticosMock as Diagnostico[])];
  return lista.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
}

export async function getImagemDoRegistro(
  registroImagemId: number
): Promise<RegistroImagem | null> {
  const imagens = imagensMock as any[];
  const encontrada = imagens.find(
    (img) => (img.id ?? img.registro_imagem_id) === registroImagemId
  );
  return (encontrada as RegistroImagem) ?? null;
}

export function getDispositivoIdUnico(): number {
  return DISPOSITIVO_UNICO_ID;
}