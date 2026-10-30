import { useState } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';

import { EXEMPLO_DURACAO, formatarDuracao, lerDuracao } from '@/utils/duracao';

import { Campo } from './Campo';

type Props = {
  rotulo?: string;
  /** Valor inicial em minutos; `null` quando não há duração. */
  inicial: number | null;
  /** Recebe os minutos (ou `null`, campo vazio) sempre que o texto é uma duração válida. */
  aoMudar: (minutos: number | null) => void;
  /** Avisa quando o texto deixa de ser uma duração válida, para a tela não salvar. */
  aoMudarValidade: (valido: boolean) => void;
  /** Mostra o erro mesmo sem a pessoa ter saído do campo (ao tentar salvar). */
  mostrarErro?: boolean;
  estilo?: StyleProp<ViewStyle>;
};

/**
 * Duração digitada, opcional. Vazio é "não informada": nenhuma duração é presumida.
 *
 * O erro aparece quando a pessoa sai do campo ou tenta salvar, não a cada tecla: "1 ho"
 * é só um "1 hora" pela metade. Valendo, o texto de ajuda mostra como será guardado.
 */
export function CampoDuracao({
  rotulo = 'Duração',
  inicial,
  aoMudar,
  aoMudarValidade,
  mostrarErro = false,
  estilo,
}: Props) {
  const [texto, setTexto] = useState(inicial ? formatarDuracao(inicial) : '');
  const [saiu, setSaiu] = useState(false);
  const leitura = lerDuracao(texto);

  const erro = leitura.tipo === 'invalida' && (saiu || mostrarErro) ? leitura.mensagem : null;
  const ajuda =
    leitura.tipo === 'valida'
      ? `Fica registrado como ${formatarDuracao(leitura.minutos)}.`
      : `${EXEMPLO_DURACAO}. Pode deixar em branco.`;

  return (
    <Campo
      rotulo={rotulo}
      valor={texto}
      aoMudar={(novo) => {
        setTexto(novo);
        const lido = lerDuracao(novo);
        aoMudarValidade(lido.tipo !== 'invalida');
        if (lido.tipo === 'vazia') aoMudar(null);
        if (lido.tipo === 'valida') aoMudar(lido.minutos);
      }}
      aoSair={() => setSaiu(true)}
      placeholder="Ex.: 1h30"
      autoCapitalize="none"
      marcaOpcional
      ajuda={ajuda}
      erro={erro}
      estilo={estilo}
    />
  );
}
