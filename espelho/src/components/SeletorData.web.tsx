import { StyleSheet, View } from 'react-native';

import { diaLocalIso, paraData } from '@/utils/datas';

import type { PropsSeletorData } from './SeletorData';

/**
 * Versão web do SeletorData: um `<input type="date">` invisível cobre o conteúdo, e o
 * toque nele abre o calendário do próprio navegador (no celular, o seletor do sistema).
 * O toque precisa cair no campo de verdade: navegadores só abrem o calendário em
 * resposta direta a um gesto da pessoa.
 */
export function SeletorData({ valor, aoEscolher, minimo, maximo, rotuloAcessivel, children, estilo }: PropsSeletorData) {
  return (
    <View style={[styles.base, estilo]}>
      {children}
      <input
        type="date"
        aria-label={rotuloAcessivel}
        value={diaLocalIso(valor)}
        min={minimo ? diaLocalIso(minimo) : undefined}
        max={maximo ? diaLocalIso(maximo) : undefined}
        onChange={(evento) => {
          const dia = evento.currentTarget.value;
          if (/^\d{4}-\d{2}-\d{2}$/.test(dia)) aoEscolher(paraData(dia));
        }}
        onClick={(evento) => {
          // Sem isto o computador só abre o calendário no ícone, que aqui está invisível.
          try {
            evento.currentTarget.showPicker?.();
          } catch {
            // Navegador sem showPicker ou que recusou: o campo continua clicável.
          }
        }}
        style={estiloEntrada}
      />
    </View>
  );
}

const estiloEntrada: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  width: '100%',
  height: '100%',
  margin: 0,
  padding: 0,
  border: 0,
  opacity: 0,
  cursor: 'pointer',
};

const styles = StyleSheet.create({
  base: { position: 'relative' },
});
