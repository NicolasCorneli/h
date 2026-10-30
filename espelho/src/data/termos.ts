import { useCallback, useEffect, useState } from 'react';

import { ErroApi, termos as apiTermos } from '@/services/api';

import type { Termo, TipoTermo } from './tipos';

/**
 * Leitura dos termos versionados, que agora vivem no servidor (tabela `termos`).
 *
 * Um termo é documento jurídico: o texto é imutável dentro de uma versão, e corrigir
 * conteúdo significa publicar uma versão nova. Antes isso dependia de publicar uma
 * versão do aplicativo; hoje não. As versões antigas continuam consultáveis, porque o
 * app precisa mostrar exatamente o texto que cada cliente aceitou.
 *
 * O cache é por versão e vive na memória da execução: o texto não muda enquanto o
 * aplicativo está aberto, e não há motivo para buscá-lo de novo a cada tela.
 */

export type { SecaoTermo, Termo, TipoTermo } from './tipos';

const cache = new Map<string, Termo>();

function chave(tipo: TipoTermo, versao?: string | null): string {
  return `${tipo}:${versao ?? 'vigente'}`;
}

async function buscar(tipo: TipoTermo, versao?: string | null): Promise<Termo> {
  const guardado = cache.get(chave(tipo, versao));
  if (guardado) return guardado;

  const termo = versao ? await apiTermos.porVersao(tipo, versao) : await apiTermos.vigente(tipo);
  cache.set(chave(tipo, versao), termo);
  // A versão vigente também fica indexada pelo número, para quando a tela pedir por ele.
  cache.set(chave(tipo, termo.versao), termo);
  return termo;
}

export type EstadoTermo = {
  termo: Termo | null;
  carregando: boolean;
  /** `naoEncontrado` indica versão desconhecida pelo servidor. */
  erro: { mensagem: string; naoEncontrado: boolean } | null;
  recarregar: () => void;
};

/**
 * Carrega um termo. Sem `versao`, traz a vigente.
 *
 * Quando a versão pedida não existe mais no servidor, a tela recebe `naoEncontrado` e
 * avisa — nunca exibe outro texto no lugar do que foi aceito.
 */
export function useTermo(tipo: TipoTermo, versao?: string | null): EstadoTermo {
  const [termo, setTermo] = useState<Termo | null>(() => cache.get(chave(tipo, versao)) ?? null);
  const [carregando, setCarregando] = useState(!termo);
  const [erro, setErro] = useState<EstadoTermo['erro']>(null);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    const guardado = cache.get(chave(tipo, versao));
    if (guardado) {
      setTermo(guardado);
      setCarregando(false);
      setErro(null);
      return () => {
        ativo = false;
      };
    }

    setCarregando(true);
    setErro(null);
    buscar(tipo, versao)
      .then((encontrado) => {
        if (!ativo) return;
        setTermo(encontrado);
      })
      .catch((falha: unknown) => {
        if (!ativo) return;
        const apiErro = falha instanceof ErroApi ? falha : null;
        setErro({
          mensagem: apiErro?.message ?? 'Não foi possível carregar o termo.',
          naoEncontrado: apiErro?.status === 404,
        });
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });

    return () => {
      ativo = false;
    };
  }, [tipo, versao, tentativa]);

  const recarregar = useCallback(() => {
    cache.delete(chave(tipo, versao));
    setTentativa((valor) => valor + 1);
  }, [tipo, versao]);

  return { termo, carregando, erro, recarregar };
}

/** Pré-carrega a versão vigente dos dois termos, para a primeira tela abrir sem espera. */
export function aquecerTermos(): void {
  void buscar('cliente').catch(() => undefined);
  void buscar('profissional').catch(() => undefined);
}
