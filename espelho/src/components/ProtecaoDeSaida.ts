import { useNavigation } from 'expo-router';
import { useCallback, useEffect, useRef } from 'react';

import { useFeedback } from './Feedback';

/**
 * Pergunta "Sair sem salvar?" quando a pessoa tenta deixar um formulário alterado.
 *
 * A tela chama `liberar()` logo depois de salvar com sucesso e **antes** de navegar.
 * Antes desta separação, a marca de "salvo" só era ligada depois que a função de salvar
 * terminava, mas essa função já levava de volta à agenda: a saída acontecia com a marca
 * ainda desligada, e a pergunta aparecia justamente para quem tinha acabado de salvar.
 */
export function useProtecaoDeSaida(alterado: boolean): { liberar: () => void } {
  const navigation = useNavigation();
  const { confirmar } = useFeedback();
  const liberado = useRef(false);

  useEffect(() => {
    const remover = navigation.addListener('beforeRemove', (evento) => {
      if (!alterado || liberado.current) return;
      evento.preventDefault();
      void confirmar({
        titulo: 'Sair sem salvar?',
        mensagem: 'O que foi preenchido nesta tela será perdido.',
        rotuloConfirmar: 'Sair sem salvar',
        rotuloCancelar: 'Continuar editando',
        destrutivo: true,
      }).then((sair) => {
        if (sair) navigation.dispatch(evento.data.action);
      });
    });
    return remover;
  }, [navigation, alterado, confirmar]);

  const liberar = useCallback(() => {
    liberado.current = true;
  }, []);

  return { liberar };
}
