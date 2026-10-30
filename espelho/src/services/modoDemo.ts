import { useEffect, useState } from 'react';

import { diagnostico } from '@/services/api';

/**
 * Se o servidor está em modo de demonstração (`MODO_DEMO=true`).
 *
 * Os atalhos de demonstração (forçar a recusa da foto, forçar a falha do serviço de
 * simulação) só têm efeito nesse modo. Fora dele, não aparecem: um botão que não faz o
 * que diz é pior do que nenhum. Na dúvida (sem resposta do servidor), fica escondido.
 */
export function useModoDemo(): boolean {
  const [demo, setDemo] = useState(false);
  useEffect(() => {
    let ativo = true;
    diagnostico
      .saude()
      .then((s) => ativo && setDemo(s.modoDemo === true))
      .catch(() => undefined);
    return () => {
      ativo = false;
    };
  }, []);
  return demo;
}
