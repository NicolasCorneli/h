import { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type KeyboardTypeOptions,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Icone } from './Icone';

type Props = {
  rotulo: string;
  valor: string;
  aoMudar: (v: string) => void;
  placeholder?: string;
  multilinha?: boolean;
  tipoTeclado?: KeyboardTypeOptions;
  segredo?: boolean;
  alternarSegredo?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words';
  /** Texto de ajuda permanente abaixo do campo. */
  ajuda?: string;
  erro?: string | null;
  obrigatorio?: boolean;
  /** Aplica uma máscara a cada digitação (ver utils/mascaras). */
  mascara?: (texto: string) => string;
  /** Chamado quando o campo perde o foco (para validar só depois de a pessoa terminar). */
  aoSair?: () => void;
  /** Rótulo opcional à direita, no lugar de "obrigatório". */
  marcaOpcional?: boolean;
  /** Máximo de caracteres: limita a digitação e mostra a contagem ao lado do rótulo. */
  limite?: number;
  estilo?: StyleProp<ViewStyle>;
};

/**
 * Campo de entrada. O rótulo fica sempre visível (não é placeholder), para que o
 * profissional saiba o que está preenchendo mesmo com o campo cheio.
 */
export function Campo({
  rotulo,
  valor,
  aoMudar,
  placeholder,
  multilinha = false,
  tipoTeclado,
  segredo = false,
  alternarSegredo = false,
  autoCapitalize = 'sentences',
  ajuda,
  erro,
  obrigatorio = false,
  mascara,
  aoSair,
  marcaOpcional = false,
  limite,
  estilo,
}: Props) {
  const [oculto, setOculto] = useState(segredo);
  const [focado, setFocado] = useState(false);

  return (
    <View style={estilo}>
      <View
        style={[
          styles.caixa,
          multilinha && styles.caixaAlta,
          focado && styles.caixaFocada,
          !!erro && styles.caixaErro,
        ]}>
        <View style={styles.linhaRotulo}>
          <Text style={textos.etiqueta}>{rotulo}</Text>
          {obrigatorio ? (
            <Text style={styles.obrigatorio}>obrigatório</Text>
          ) : marcaOpcional ? (
            <Text style={styles.obrigatorio}>opcional</Text>
          ) : limite ? (
            <Text style={styles.obrigatorio} accessibilityLabel={`${valor.length} de ${limite} caracteres`}>
              {valor.length}/{limite}
            </Text>
          ) : null}
        </View>
        <View style={styles.linha}>
          <TextInput
            value={valor}
            maxLength={limite}
            onChangeText={(t) => aoMudar(mascara ? mascara(t) : t)}
            onFocus={() => setFocado(true)}
            onBlur={() => {
              setFocado(false);
              aoSair?.();
            }}
            placeholder={placeholder}
            placeholderTextColor={cores.placeholder}
            multiline={multilinha}
            keyboardType={tipoTeclado}
            secureTextEntry={oculto}
            autoCapitalize={autoCapitalize}
            accessibilityLabel={obrigatorio ? `${rotulo}, obrigatório` : rotulo}
            accessibilityHint={ajuda}
            style={[styles.entrada, multilinha && styles.entradaAlta]}
          />
          {alternarSegredo ? (
            <Pressable
              onPress={() => setOculto((v) => !v)}
              accessibilityRole="button"
              accessibilityLabel={oculto ? 'Mostrar senha' : 'Ocultar senha'}
              hitSlop={12}>
              <Text style={styles.alternar}>{oculto ? 'mostrar' : 'ocultar'}</Text>
            </Pressable>
          ) : null}
        </View>
      </View>

      {erro ? (
        <View style={styles.aviso} accessibilityLiveRegion="polite">
          <Icone nome="alerta" tamanho={13} cor={cores.erroTexto} />
          <Text style={styles.erro}>{erro}</Text>
        </View>
      ) : ajuda ? (
        <Text style={styles.ajuda}>{ajuda}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  caixa: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingTop: espaco.md,
    paddingBottom: espaco.sm,
  },
  caixaAlta: { minHeight: 108 },
  caixaFocada: { borderColor: cores.acaoTexto },
  caixaErro: { borderColor: cores.erro },
  linhaRotulo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: espaco.sm,
  },
  obrigatorio: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 10,
    color: cores.textoApoio,
  },
  linha: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: espaco.md,
  },
  entrada: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 15,
    lineHeight: 20,
    color: cores.texto,
    paddingVertical: espaco.xs,
    paddingHorizontal: 0,
  },
  entradaAlta: {
    fontFamily: 'FamiljenGrotesk_400Regular',
    lineHeight: 22,
    minHeight: 72,
    textAlignVertical: 'top',
  },
  alternar: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 13,
    color: cores.acaoTexto,
    paddingBottom: espaco.sm,
  },
  aviso: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.sm,
    marginTop: espaco.sm,
    marginLeft: espaco.xs,
  },
  erro: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 13,
    lineHeight: 18,
    color: cores.erroTexto,
  },
  ajuda: {
    fontFamily: 'FamiljenGrotesk_400Regular',
    fontSize: 12,
    lineHeight: 17,
    color: cores.textoApoio,
    marginTop: espaco.sm,
    marginLeft: espaco.xs,
  },
});
