/**
 * Dados do módulo financeiro, guardados no AsyncStorage do aparelho e
 * iniciados a partir de src/mocks/gastos.json na primeira execução. Não
 * são sincronizados com a API.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import gastosMock from '../mocks/gastos.json';

export interface Gasto {
  id: string;
  categoria: string;
  descricao: string;
  valor: number;
  data: string; // ISO 8601
}

export interface ResumoPorCategoria {
  categoria: string;
  total: number;
}

export interface ResumoFinanceiro {
  totalGasto: number;
  quantidadeLancamentos: number;
  porCategoria: ResumoPorCategoria[];
  mesReferencia: string; // formato "YYYY-MM"
}

// Categorias padrão sugeridas pro formulário. Ajuste livremente depois.
export const CATEGORIAS_GASTO = [
  'Fungicida',
  'Fertilizante',
  'Mão de obra',
  'Energia',
  'Sementes',
  'Outro',
] as const;

const STORAGE_KEY = '@ecovision:gastos';

// Cache em memória pra evitar releituras repetidas do AsyncStorage
// dentro da mesma sessão do app.
let cache: Gasto[] | null = null;

async function carregarGastosDoStorage(): Promise<Gasto[]> {
  if (cache) return cache;

  try {
    const salvos = await AsyncStorage.getItem(STORAGE_KEY);
    if (salvos) {
      cache = JSON.parse(salvos) as Gasto[];
    } else {
      // Primeira execução no dispositivo: semeia com o mock e já persiste.
      cache = [...(gastosMock as Gasto[])];
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    }
  } catch (e) {
    console.warn('Falha ao ler gastos do AsyncStorage, usando mock em memória.', e);
    cache = [...(gastosMock as Gasto[])];
  }

  return cache;
}

async function salvarGastosNoStorage(gastos: Gasto[]): Promise<void> {
  cache = gastos;
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(gastos));
  } catch (e) {
    console.warn('Falha ao salvar gastos no AsyncStorage.', e);
  }
}

function gerarId(): string {
  return `g${Date.now()}`;
}

function mesmoMes(dataIso: string, referencia: Date): boolean {
  const d = new Date(dataIso);
  return (
    d.getFullYear() === referencia.getFullYear() &&
    d.getMonth() === referencia.getMonth()
  );
}

/** Lista completa de gastos (todos os meses), mais recente primeiro. */
export async function getGastos(): Promise<Gasto[]> {
  const gastos = await carregarGastosDoStorage();
  return [...gastos].sort(
    (a, b) => new Date(b.data).getTime() - new Date(a.data).getTime()
  );
}

/** Lista de gastos apenas do mês de referência (padrão: mês atual), mais recente primeiro. */
export async function getGastosPorMes(
  referencia: Date = new Date()
): Promise<Gasto[]> {
  const gastos = await carregarGastosDoStorage();
  return gastos
    .filter((g) => mesmoMes(g.data, referencia))
    .sort((a, b) => new Date(b.data).getTime() - new Date(a.data).getTime());
}

/**
 * Resumo financeiro do mês de referência (padrão: mês atual), com total e
 * detalhamento por categoria apenas daquele mês.
 */
export async function getResumoFinanceiro(
  referencia: Date = new Date()
): Promise<ResumoFinanceiro> {
  const gastosDoMes = await getGastosPorMes(referencia);

  const totalGasto = gastosDoMes.reduce((soma, g) => soma + g.valor, 0);

  const totaisPorCategoria = new Map<string, number>();
  gastosDoMes.forEach((g) => {
    totaisPorCategoria.set(
      g.categoria,
      (totaisPorCategoria.get(g.categoria) || 0) + g.valor
    );
  });

  const porCategoria: ResumoPorCategoria[] = Array.from(
    totaisPorCategoria.entries()
  )
    .map(([categoria, total]) => ({ categoria, total }))
    .sort((a, b) => b.total - a.total);

  const anoRef = referencia.getFullYear();
  const mesRef = referencia.getMonth();
  const mesReferencia = `${anoRef}-${String(mesRef + 1).padStart(2, '0')}`;

  return {
    totalGasto,
    quantidadeLancamentos: gastosDoMes.length,
    porCategoria,
    mesReferencia,
  };
}

/** Soma de todos os gastos já registrados, em qualquer mês/ano. */
export async function getGastoTotalGeral(): Promise<number> {
  const gastos = await carregarGastosDoStorage();
  return gastos.reduce((soma, g) => soma + g.valor, 0);
}

export async function registrarGasto(
  novoGasto: Omit<Gasto, 'id'>
): Promise<Gasto> {
  const gastos = await carregarGastosDoStorage();
  const gasto: Gasto = { ...novoGasto, id: gerarId() };
  const atualizados = [gasto, ...gastos];
  await salvarGastosNoStorage(atualizados);
  return gasto;
}

/**
 * Remove um gasto pelo id. Devolve true se algum item foi removido e false
 * se o id não existia.
 */
export async function excluirGasto(id: string): Promise<boolean> {
  const gastos = await carregarGastosDoStorage();
  const atualizados = gastos.filter((g) => g.id !== id);

  if (atualizados.length === gastos.length) {
    return false; // nada foi removido
  }

  await salvarGastosNoStorage(atualizados);
  return true;
}

/** Útil pra demo/testes: restaura os dados originais do mock. */
export async function resetarGastosParaMock(): Promise<void> {
  await salvarGastosNoStorage([...(gastosMock as Gasto[])]);
}