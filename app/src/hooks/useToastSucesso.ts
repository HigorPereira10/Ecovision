/**
 * app/src/hooks/useToastSucesso.ts
 *
 * Controla a exibição temporária de uma mensagem de sucesso
 * (ToastSucesso). mostrarToast('texto') exibe por `duracaoMs` e some
 * sozinho — sem precisar o chamador gerenciar timers.
 */

import { useCallback, useRef, useState } from 'react';

export function useToastSucesso(duracaoMs: number = 2500) {
  const [mensagem, setMensagem] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mostrarToast = useCallback(
    (texto: string) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      setMensagem(texto);
      timeoutRef.current = setTimeout(() => setMensagem(null), duracaoMs);
    },
    [duracaoMs]
  );

  return { mensagem, mostrarToast };
}