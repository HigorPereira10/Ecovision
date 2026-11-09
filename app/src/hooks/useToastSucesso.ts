/**
 * Controla a exibição temporária do ToastSucesso: mostrarToast('texto')
 * exibe a mensagem por `duracaoMs` e a oculta automaticamente.
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