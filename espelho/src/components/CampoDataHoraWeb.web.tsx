import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Icone } from './Icone';
import type { PropsCampoDataHoraWeb } from './CampoDataHoraWeb';

/**
 * Data ou horário no navegador, com o campo do próprio navegador (`<input type="date">` e
 * `type="time"`), com a mesma moldura dos outros campos.
 *
 * Substitui o campo de texto com máscara. A máscara juntava os dígitos e os repartia de
 * novo a cada tecla: apagar um número no meio de "01/12/2026" fazia todos os seguintes
 * andarem uma casa ("01/12/026"). No campo do navegador, dia, mês e ano (ou hora e
 * minuto) são segmentos separados: apagar um número só esvazia aquele segmento, e o
 * computador ainda oferece o calendário.
 *
 * O valor fica num estado próprio. Com um segmento vazio, o navegador informa valor vazio
 * e marca a entrada como incompleta (`validity.badInput`); devolver o valor antigo ao campo
 * apagaria o que a pessoa já digitou nos outros segmentos.
 */
export function CampoDataHoraWeb({
  rotulo,
  tipo,
  valor,
  aoMudar,
  minimo,
  maximo,
  erro,
  ajuda,
  estilo,
}: PropsCampoDataHoraWeb) {
  const [texto, setTexto] = useState(valor);
  const [focado, setFocado] = useState(false);
  // O `valor` da tela na renderização anterior. Só quando ele muda o campo se
  // ressincroniza, e só se ficou diferente do que está escrito (uma troca feita por outra
  // parte da tela). Um valor que a tela recusou (como o ano "0002" enquanto se digita
  // "2027") não muda o `valor`, e o que a pessoa digitou fica no campo.
  const [valorAnterior, setValorAnterior] = useState(valor);
  if (valor !== valorAnterior) {
    setValorAnterior(valor);
    if (valor !== texto) setTexto(valor);
  }

  return (
    <View style={estilo}>
      <View style={[styles.caixa, focado && styles.caixaFocada, !!erro && styles.caixaErro]}>
        <Text style={textos.etiqueta}>{rotulo}</Text>
        <input
          type={tipo === 'data' ? 'date' : 'time'}
          lang="pt-BR"
          aria-label={rotulo}
          aria-invalid={!!erro}
          value={texto}
          min={minimo}
          max={maximo}
          onFocus={() => setFocado(true)}
          onBlur={() => setFocado(false)}
          onChange={(evento) => {
            const campo = evento.currentTarget;
            setTexto(campo.value);
            if (campo.value) aoMudar(campo.value);
            else aoMudar(campo.validity.badInput ? null : '');
          }}
          style={estiloEntrada}
        />
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

const estiloEntrada: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  border: 0,
  outline: 'none',
  background: 'transparent',
  padding: `${espaco.xs}px 0`,
  margin: 0,
  fontFamily: 'FamiljenGrotesk_500Medium, system-ui, sans-serif',
  fontSize: 15,
  lineHeight: '20px',
  color: cores.texto,
  colorScheme: 'light',
  cursor: 'text',
};

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
  caixaFocada: { borderColor: cores.acaoTexto },
  caixaErro: { borderColor: cores.erro },
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
