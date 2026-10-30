import { StyleSheet, Text, View } from 'react-native';

import { useSuperficie } from '@/theme/superficie';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

import { BotaoIcone } from './Basicos';

type Props = {
  titulo: string;
  subtitulo?: string;
  aoVoltar?: () => void;
  rotuloVoltar?: string;
  /** Ícone do botão à esquerda: seta para telas empilhadas, ✕ para fluxos modais. */
  iconeVoltar?: 'voltar' | 'fechar';
  direita?: React.ReactNode;
  comLinha?: boolean;
  /** Título grande em serifada — usado nas telas raiz das abas. */
  grande?: boolean;
};

/** Cabeçalho único de todas as telas: mesma altura, mesmo alinhamento, mesmo alvo de toque. */
export function Cabecalho({
  titulo,
  subtitulo,
  aoVoltar,
  rotuloVoltar = 'Voltar',
  iconeVoltar = 'voltar',
  direita,
  comLinha = true,
  grande = false,
}: Props) {
  // Sobre a faixa escura o texto é claro; dentro de uma folha clara, escuro.
  const escuro = useSuperficie() === 'escura';
  const estilos = escuro ? textosEscuros : textos;
  return (
    <View style={[styles.base, comLinha && !escuro && styles.comLinha]}>
      {aoVoltar ? (
        <BotaoIcone icone={iconeVoltar} aoPressionar={aoVoltar} rotuloAcessivel={rotuloVoltar} />
      ) : null}
      <View style={styles.centro}>
        <Text
          style={grande ? estilos.titulo : estilos.corpoForte}
          accessibilityRole="header"
          numberOfLines={2}>
          {titulo}
        </Text>
        {subtitulo ? <Text style={[estilos.meta, styles.subtitulo]}>{subtitulo}</Text> : null}
      </View>
      {direita}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.sm,
    paddingBottom: espaco.md,
  },
  comLinha: {
    borderBottomWidth: 1,
    borderBottomColor: cores.bordaSuave,
  },
  centro: { flex: 1 },
  subtitulo: { marginTop: 2 },
});

// `Tela` põe os cabeçalhos do topo sobre a faixa escura, antes da folha de conteúdo.
Cabecalho.naFaixaEscura = true;
