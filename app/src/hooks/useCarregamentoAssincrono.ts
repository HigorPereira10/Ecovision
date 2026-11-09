/**
 * Hook dos estados de carregamento, erro e atualização (pull-to-refresh)
 * das telas que consomem services/*.ts.
 *
 * - Na carga inicial ou em nova tentativa, um erro deixa `dados` como
 *   null, e a tela mostra o EstadoErro.
 * - Em uma atualização que falha, os últimos dados são mantidos e a tela
 *   pode exibir um aviso não bloqueante (AvisoErroInline).
 * - Os dados são recarregados sempre que a tela volta ao foco.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { obterMensagemErro } from '../utils/erros';

type ModoExecucao = 'inicial' | 'atualizacao' | 'nova_tentativa';

interface ResultadoCarregamentoAssincrono<T> {
  dados: T | null;
  carregando: boolean;
  atualizando: boolean;
  erro: string | null;
  recarregar: () => Promise<void>;
  atualizar: () => Promise<void>;
}

export function useCarregamentoAssincrono<T>(
  buscarDados: () => Promise<T>,
  deps: React.DependencyList = [],
  recarregarAoFocar: boolean = true
): ResultadoCarregamentoAssincrono<T> {
  const [dados, setDados] = useState<T | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [atualizando, setAtualizando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Evita setState numa tela que já desmontou (ex: usuário trocou de
  // aba antes da Promise resolver).
  const montadoRef = useRef(true);
  useEffect(() => {
    montadoRef.current = true;
    return () => {
      montadoRef.current = false;
    };
  }, []);

  const executar = useCallback(
    async (modo: ModoExecucao) => {
      if (modo === 'atualizacao') {
        setAtualizando(true);
      } else {
        setCarregando(true);
        setErro(null);
      }

      try {
        const resultado = await buscarDados();
        if (!montadoRef.current) return;
        setDados(resultado);
        setErro(null);
      } catch (e) {
        if (!montadoRef.current) return;
        setErro(obterMensagemErro(e));
      } finally {
        if (!montadoRef.current) return;
        if (modo === 'atualizacao') setAtualizando(false);
        else setCarregando(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    deps
  );

  useEffect(() => {
    executar('inicial');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  // O primeiro foco acontece JUNTO com a montagem, e sem esta guarda
  // toda tela faria duas requisições iguais ao abrir.
  const primeiroFoco = useRef(true);

  useFocusEffect(
    useCallback(() => {
      if (primeiroFoco.current) {
        primeiroFoco.current = false;
        return;
      }
      if (!recarregarAoFocar) return;

      // Modo 'atualizacao' de propósito: mantém o que já está na tela
      // enquanto busca. Usar 'inicial' faria a tela piscar o spinner de
      // tela cheia a cada troca de aba.
      executar('atualizacao');
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [executar, recarregarAoFocar])
  );

  const recarregar = useCallback(() => executar('nova_tentativa'), [executar]);
  const atualizar = useCallback(() => executar('atualizacao'), [executar]);

  return { dados, carregando, atualizando, erro, recarregar, atualizar };
}
