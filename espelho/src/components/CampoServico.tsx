import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { SERVICOS } from '@/data/catalogo';
import { espaco } from '@/theme/tokens';

import { Chip, Etiqueta } from './Basicos';
import { Campo } from './Campo';

/** Rótulo da opção livre. Nunca é gravado: o que vai para o banco é o texto digitado. */
export const OUTRO = 'Outro';

type Props = {
  rotulo: string;
  /**
   * Serviço inicial. Um da lista seleciona o chip; qualquer outro texto abre "Outro" já
   * preenchido com ele (serviço digitado antes, ou que saiu da lista); vazio não seleciona
   * nada.
   */
  inicial: string;
  /** Recebe o serviço escolhido: o nome da lista ou o texto digitado em "Outro". */
  aoMudar: (servico: string) => void;
  erro?: string | null;
  rotuloOutro?: string;
};

function escolhaInicial(servico: string): string | null {
  if (!servico) return null;
  return (SERVICOS as readonly string[]).includes(servico) ? servico : OUTRO;
}

/** Serviços da lista, mais "Outro" com descrição livre. O mesmo em todo o aplicativo. */
export function CampoServico({ rotulo, inicial, aoMudar, erro, rotuloOutro = 'Qual serviço?' }: Props) {
  const [escolha, setEscolha] = useState<string | null>(escolhaInicial(inicial));
  const [outro, setOutro] = useState(escolhaInicial(inicial) === OUTRO ? inicial : '');

  const escolher = (opcao: string) => {
    setEscolha(opcao);
    aoMudar(opcao === OUTRO ? outro.trim() : opcao);
  };

  return (
    <View>
      <Etiqueta estilo={styles.etiqueta}>{rotulo}</Etiqueta>
      <View style={styles.chips} accessibilityRole="radiogroup">
        {[...SERVICOS, OUTRO].map((s) => (
          <Chip key={s} texto={s} ativo={escolha === s} aoPressionar={() => escolher(s)} />
        ))}
      </View>
      {escolha === OUTRO ? (
        <Campo
          rotulo={rotuloOutro}
          valor={outro}
          aoMudar={(texto) => {
            setOutro(texto);
            aoMudar(texto.trim());
          }}
          placeholder="Por exemplo: penteado para festa"
          erro={erro}
          estilo={styles.campo}
        />
      ) : null}
    </View>
  );
}

/** Mensagem de validação do serviço, a mesma nos três formulários. */
export function erroDoServico(servico: string): string | null {
  if (!servico) return 'Escolha o serviço, ou escreva qual foi em "Outro".';
  if (servico.length < 2) return 'Escreva qual é o serviço.';
  if (servico.toLowerCase() === OUTRO.toLowerCase()) return 'Escreva qual é o serviço, em vez de "Outro".';
  return null;
}

const styles = StyleSheet.create({
  etiqueta: { marginTop: espaco.xl, marginBottom: espaco.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.sm },
  campo: { marginTop: espaco.md },
});
