/**
 * app/src/hooks/useCarregamentoAssincrono.ts
 *
 * Hook compartilhado por todas as telas que consomem a camada de
 * serviço (services/*.ts). Padroniza os estados de UI que toda tela
 * baseada em dados assíncronos precisa tratar — carregando, erro e
 * atualizando (pull-to-refresh) — evitando repetir esse boilerplate
 * nas 5 telas do app.
 *
 * Comportamento importante:
 * - Na carga inicial (ou numa nova tentativa via botão "Tentar
 *   novamente"), um erro deixa `dados` como null: quem usa o hook
 *   deve mostrar o EstadoErro de tela cheia nesse caso.
 * - Num pull-to-refresh que falha, os últimos dados carregados com
 *   sucesso são MANTIDOS na tela (não somem) — quem usa o hook pode
 *   mostrar um aviso não-bloqueante (ver AvisoErroInline) sem perder
 *   o que já estava na tela. Falha de rede não deve apagar o último
 *   dado bom conhecido.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
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
  deps: React.DependencyList = []
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

  const recarregar = useCallback(() => executar('nova_tentativa'), [executar]);
  const atualizar = useCallback(() => executar('atualizacao'), [executar]);

  return { dados, carregando, atualizando, erro, recarregar, atualizar };
}
