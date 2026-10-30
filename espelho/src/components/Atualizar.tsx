import { useCallback, useState } from 'react';
import { RefreshControl } from 'react-native';

import { useStore } from '@/data/store';
import { cores } from '@/theme/tokens';

/**
 * Puxar para atualizar.
 *
 * Com os dados no servidor, a tela pode estar desatualizada — outro aparelho, outra aba,
 * uma simulação que terminou depois. Antes da integração não havia o que recarregar.
 */
export function useAtualizar() {
  const { acoes } = useStore();
  const [atualizando, setAtualizando] = useState(false);

  const atualizar = useCallback(async () => {
    setAtualizando(true);
    try {
      await acoes.recarregar();
    } finally {
      setAtualizando(false);
    }
  }, [acoes]);

  const controle = (
    <RefreshControl
      refreshing={atualizando}
      onRefresh={() => void atualizar()}
      colors={[cores.acao]}
      tintColor={cores.acao}
      title="Atualizando…"
    />
  );

  return { controle, atualizando, atualizar };
}
