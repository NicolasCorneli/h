import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, diaLocalIso, hora as formatarHora, isoDeDataCurta, paraData } from '@/utils/datas';
import { mascaraData, mascaraHora } from '@/utils/mascaras';

import { Campo } from './Campo';
import { Icone } from './Icone';
import { SeletorData } from './SeletorData';

type Props = {
  rotulo: string;
  /** Data e hora corrente do campo. */
  valor: Date;
  aoMudar: (data: Date) => void;
  modo: 'data' | 'hora';
  erro?: string | null;
  estilo?: StyleProp<ViewStyle>;
  /** Avisa a tela quando o que está digitado deixa de ser um valor válido. */
  aoMudarValidade?: (valido: boolean) => void;
  /** Data mínima aceita (só o dia conta). Usada para impedir agendamento no passado. */
  minimo?: Date;
};

/** Início do dia, no horário local do aparelho. */
function inicioDoDia(data: Date): Date {
  const d = new Date(data);
  d.setHours(0, 0, 0, 0);
  return d;
}

/**
 * Data: seletor nativo no celular, campo com máscara no navegador — o seletor valida
 * mês e dia por conta própria, e no navegador ele não existe.
 *
 * Hora: campo digitado em toda plataforma. O seletor nativo de hora (roda ou relógio)
 * exige vários gestos para uma informação que o profissional já sabe de cor; digitar
 * `14:30` é mais rápido e menos sujeito a engano. Em troca, a validação passa a ser
 * responsabilidade daqui: formato, faixa de horas e minutos, e recusa de valor
 * incompleto.
 */
export function CampoData({ rotulo, valor, aoMudar, modo, erro, estilo, aoMudarValidade, minimo }: Props) {
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState(modo === 'data' ? dataCurta(valor.toISOString()) : formatarHora(valor.toISOString()));
  const [erroInterno, setErroInterno] = useState<string | null>(null);

  const digitado = modo === 'hora' || Platform.OS === 'web';

  if (digitado) {
    return (
      <Campo
        rotulo={rotulo}
        valor={texto}
        aoMudar={(entrada) => {
          const formatado = modo === 'data' ? mascaraData(entrada) : mascaraHora(entrada);
          setTexto(formatado);
          const convertido = converter(formatado, modo, valor);
          if (convertido && modo === 'data' && minimo && inicioDoDia(convertido) < inicioDoDia(minimo)) {
            // Dia anterior ao mínimo: a data é bem formada, mas não é aceita.
            setErroInterno('Escolha uma data a partir de hoje.');
            aoMudarValidade?.(false);
            return;
          }
          if (convertido) {
            setErroInterno(null);
            aoMudarValidade?.(true);
            aoMudar(convertido);
            return;
          }
          // Enquanto o campo está pela metade não se acusa erro — seria reclamar antes
          // de a pessoa terminar de digitar. Vazio e completo-porém-inválido, sim.
          const completo = modo === 'data' ? formatado.length === 10 : formatado.length === 5;
          const mensagem = !formatado
            ? modo === 'data'
              ? 'Informe a data.'
              : 'Informe o horário.'
            : completo
              ? modo === 'data'
                ? 'Data inválida. Use dd/mm/aaaa.'
                : 'Horário inválido. Use HH:MM, entre 00:00 e 23:59.'
              : modo === 'data'
                ? 'Data incompleta. Use dd/mm/aaaa.'
                : 'Horário incompleto. Use HH:MM, por exemplo 09:30.';
          setErroInterno(mensagem);
          aoMudarValidade?.(false);
        }}
        placeholder={modo === 'data' ? 'dd/mm/aaaa' : 'HH:MM'}
        tipoTeclado={modo === 'hora' ? 'number-pad' : 'numbers-and-punctuation'}
        erro={erro ?? erroInterno}
        estilo={estilo}
      />
    );
  }

  const exibicao = modo === 'data' ? dataCurta(valor.toISOString()) : formatarHora(valor.toISOString());

  return (
    <View style={estilo}>
      <Pressable
        onPress={() => setAberto(true)}
        accessibilityRole="button"
        accessibilityLabel={`${rotulo}: ${exibicao}. Toque para alterar`}
        style={({ pressed }) => [styles.caixa, !!erro && styles.caixaErro, pressed && styles.pressionado]}>
        <View style={styles.texto}>
          <Text style={textos.etiqueta}>{rotulo}</Text>
          <Text style={styles.valor}>{exibicao}</Text>
        </View>
        <Icone nome={modo === 'data' ? 'calendario' : 'relogio'} tamanho={18} />
      </Pressable>
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}

      {aberto ? (
        <DateTimePicker
          value={valor}
          mode={modo === 'data' ? 'date' : 'time'}
          minimumDate={modo === 'data' && minimo ? inicioDoDia(minimo) : undefined}
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onChange={(_evento, escolhida) => {
            setAberto(Platform.OS === 'ios');
            if (escolhida) aoMudar(escolhida);
          }}
        />
      ) : null}
    </View>
  );
}

type PropsOpcional = {
  rotulo: string;
  /** Data em dd/mm/aaaa, ou vazio quando não informada. */
  valor: string;
  aoMudar: (texto: string) => void;
  /** Dia em que o calendário abre quando o campo está vazio. */
  inicial: Date;
  minimo?: Date;
  maximo?: Date;
  ajuda?: string;
  erro?: string | null;
};

/**
 * Data que pode ficar em branco (nascimento). No celular, o calendário do sistema, com a
 * opção de limpar; no navegador, o mesmo campo digitado dd/mm/aaaa de antes.
 *
 * O valor continua sendo o texto dd/mm/aaaa nos dois casos, então a tela valida e envia
 * do mesmo jeito.
 */
export function CampoDataOpcional({ rotulo, valor, aoMudar, inicial, minimo, maximo, ajuda, erro }: PropsOpcional) {
  if (Platform.OS === 'web') {
    return (
      <Campo
        rotulo={rotulo}
        valor={valor}
        aoMudar={aoMudar}
        placeholder="dd/mm/aaaa"
        tipoTeclado="number-pad"
        mascara={mascaraData}
        ajuda={ajuda}
        erro={erro}
      />
    );
  }

  const iso = isoDeDataCurta(valor);
  return (
    <View>
      <SeletorData
        valor={iso ? paraData(iso) : inicial}
        aoEscolher={(data) => aoMudar(dataCurta(diaLocalIso(data)))}
        minimo={minimo}
        maximo={maximo}
        rotuloAcessivel={`${rotulo}: ${valor || 'não informada'}. Toque para escolher no calendário`}
        estilo={[styles.caixa, !!erro && styles.caixaErro]}>
        <View style={styles.texto}>
          <Text style={textos.etiqueta}>{rotulo}</Text>
          <Text style={valor ? styles.valor : styles.vazio}>{valor || 'Toque para escolher'}</Text>
        </View>
        <Icone nome="calendario" tamanho={18} />
      </SeletorData>
      {erro ? (
        <Text style={styles.erro}>{erro}</Text>
      ) : ajuda ? (
        <Text style={styles.ajuda}>{ajuda}</Text>
      ) : null}
      {valor ? (
        <Pressable
          onPress={() => aoMudar('')}
          accessibilityRole="button"
          accessibilityLabel={`Limpar ${rotulo.toLowerCase()}`}
          hitSlop={8}
          style={styles.limpar}>
          <Text style={styles.limparTexto}>Limpar data</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function converter(texto: string, modo: 'data' | 'hora', base: Date): Date | null {
  if (modo === 'data') {
    const partes = texto.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!partes) return null;
    const [, dia, mes, ano] = partes;
    const data = new Date(Number(ano), Number(mes) - 1, Number(dia), base.getHours(), base.getMinutes());
    if (Number.isNaN(data.getTime()) || data.getDate() !== Number(dia)) return null;
    return data;
  }
  const partes = texto.match(/^(\d{2}):(\d{2})$/);
  if (!partes) return null;
  const [, h, min] = partes;
  if (Number(h) > 23 || Number(min) > 59) return null;
  const data = new Date(base);
  data.setHours(Number(h), Number(min), 0, 0);
  return data;
}

const styles = StyleSheet.create({
  caixa: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    minHeight: 64,
  },
  caixaErro: { borderColor: cores.erro },
  texto: { flex: 1, gap: espaco.xs },
  valor: { fontFamily: 'FamiljenGrotesk_500Medium', fontSize: 15, color: cores.texto },
  vazio: { fontFamily: 'FamiljenGrotesk_400Regular', fontSize: 15, color: cores.placeholder },
  ajuda: {
    fontFamily: 'FamiljenGrotesk_400Regular',
    fontSize: 12,
    lineHeight: 17,
    color: cores.textoApoio,
    marginTop: espaco.sm,
    marginLeft: espaco.xs,
  },
  limpar: { alignSelf: 'flex-start', marginTop: espaco.sm, marginLeft: espaco.xs },
  limparTexto: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 13, color: cores.acaoTexto },
  erro: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 13,
    color: cores.erroTexto,
    marginTop: espaco.sm,
    marginLeft: espaco.xs,
  },
  pressionado: { opacity: 0.85 },
});
