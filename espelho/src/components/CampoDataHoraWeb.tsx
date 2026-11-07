import type { StyleProp, ViewStyle } from 'react-native';

export type PropsCampoDataHoraWeb = {
  rotulo: string;
  tipo: 'data' | 'hora';
  /** "AAAA-MM-DD" (data) ou "HH:MM" (hora); vazio quando não há valor. */
  valor: string;
  /**
   * O valor completo, no mesmo formato; "" quando a pessoa limpou o campo; null quando
   * ele está preenchido pela metade (um segmento vazio).
   */
  aoMudar: (valor: string | null) => void;
  minimo?: string;
  maximo?: string;
  erro?: string | null;
  ajuda?: string;
  estilo?: StyleProp<ViewStyle>;
};

/**
 * Só existe na web (CampoDataHoraWeb.web.tsx): no celular, data e hora usam o seletor
 * nativo e o campo digitado de `CampoData`. Este arquivo dá o tipo às telas e não desenha
 * nada.
 */
export function CampoDataHoraWeb(_props: PropsCampoDataHoraWeb): null {
  return null;
}
