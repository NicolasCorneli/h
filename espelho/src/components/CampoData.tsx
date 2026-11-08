import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, diaLocalIso, hora as formatarHora, isoDeDataCurta, paraData, situacaoDataCurta } from '@/utils/datas';
import { digitarData, mascaraHora, normalizarDataDigitada } from '@/utils/mascaras';

import { Campo } from './Campo';
import { CampoDataHoraWeb } from './CampoDataHoraWeb';
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
 * Data: seletor nativo no celular; no navegador, o campo de data do próprio navegador
 * (`CampoDataHoraWeb`), que se digita por segmentos e também abre o calendário.
 *
 * Hora: no celular, campo digitado. O seletor nativo de hora (roda ou relógio) exige
 * vários gestos para uma informação que o profissional já sabe de cor; digitar `14:30` é
 * mais rápido e menos sujeito a engano. Em troca, a validação passa a ser
 * responsabilidade daqui: formato, faixa de horas e minutos, e recusa de valor
 * incompleto. No navegador, o campo de horário do navegador, também digitado.
 *
 * O campo com máscara deixou de ser usado no navegador porque reparte os dígitos de novo
 * a cada tecla: apagar um número no meio da data deslocava todos os seguintes.
 */
export function CampoData({ rotulo, valor, aoMudar, modo, erro, estilo, aoMudarValidade, minimo }: Props) {
  const [aberto, setAberto] = useState(false);
  // Texto do horário digitado no celular (a data no celular é pelo seletor, e na web o navegador guarda o texto).
  const [texto, setTexto] = useState(formatarHora(valor.toISOString()));
  const [erroInterno, setErroInterno] = useState<string | null>(null);

  if (Platform.OS === 'web') {
    return (
      <CampoDataHoraWeb
        rotulo={rotulo}
        tipo={modo}
        valor={modo === 'data' ? diaLocalIso(valor) : formatarHora(valor.toISOString())}
        minimo={modo === 'data' && minimo ? diaLocalIso(minimo) : undefined}
        aoMudar={(entrada) => {
          const mensagem = (texto: string) => {
            setErroInterno(texto);
            aoMudarValidade?.(false);
          };
          if (entrada === null) {
            return mensagem(
              modo === 'data' ? 'Data incompleta: preencha dia, mês e ano.' : 'Horário incompleto: preencha hora e minuto.'
            );
          }
          if (entrada === '') return mensagem(modo === 'data' ? 'Informe a data.' : 'Informe o horário.');
          const convertido = deEntradaWeb(entrada, modo, valor);
          if (!convertido) return mensagem('Confira o ano: use quatro dígitos, como 2026.');
          if (modo === 'data' && minimo && inicioDoDia(convertido) < inicioDoDia(minimo)) {
            return mensagem('Escolha uma data a partir de hoje.');
          }
          setErroInterno(null);
          aoMudarValidade?.(true);
          aoMudar(convertido);
        }}
        erro={erro ?? erroInterno}
        estilo={estilo}
      />
    );
  }

  if (modo === 'hora') {
    return (
      <Campo
        rotulo={rotulo}
        valor={texto}
        aoMudar={(entrada) => {
          const formatado = mascaraHora(entrada);
          setTexto(formatado);
          const convertido = converterHora(formatado, valor);
          if (convertido) {
            setErroInterno(null);
            aoMudarValidade?.(true);
            aoMudar(convertido);
            return;
          }
          const mensagem = !formatado
            ? 'Informe o horário.'
            : formatado.length === 5
              ? 'Horário inválido. Use HH:MM, entre 00:00 e 23:59.'
              : 'Horário incompleto. Use HH:MM, por exemplo 09:30.';
          setErroInterno(mensagem);
          aoMudarValidade?.(false);
        }}
        placeholder="HH:MM"
        tipoTeclado="number-pad"
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
 * Data que pode ficar em branco (nascimento): digitada (dd/mm/aaaa), com o calendário num
 * botão ao lado. O mesmo campo no celular e no navegador.
 *
 * A digitação não tem regra rígida (`digitarData`): as barras entram sozinhas, nada é
 * reorganizado quando se apaga ou corrige no meio, e ao sair do campo as formas comuns
 * ("4/5/2000", "04052000") viram dd/mm/aaaa. Se a data existe, quem diz é
 * `situacaoDataCurta`, e só no fim: data impossível (31/04, 29/02 em ano comum, mês 13)
 * quando os oito números estão lá; incompleta só depois que a pessoa sai do campo, e o
 * aviso some assim que ela volta a digitar.
 *
 * O valor é o texto dd/mm/aaaa, convertido para AAAA-MM-DD pela tela ao salvar
 * (`isoDeDataCurta`).
 */
export function CampoDataOpcional({ rotulo, valor, aoMudar, inicial, minimo, maximo, ajuda, erro }: PropsOpcional) {
  const [saiu, setSaiu] = useState(false);
  const iso = isoDeDataCurta(valor);
  const situacao = situacaoDataCurta(valor);
  const aviso =
    situacao === 'invalida'
      ? 'Essa data não existe. Confira o dia e o mês.'
      : situacao === 'incompleta' && saiu
        ? 'Data incompleta: use dd/mm/aaaa, por exemplo 04/05/2000.'
        : iso && maximo && iso > diaLocalIso(maximo)
          ? 'A data não pode estar no futuro.'
          : iso && minimo && iso < diaLocalIso(minimo)
            ? 'Confira o ano.'
            : null;

  return (
    <View>
      <Campo
        rotulo={rotulo}
        valor={valor}
        aoMudar={(texto) => {
          setSaiu(false);
          aoMudar(digitarData(valor, texto));
        }}
        placeholder="dd/mm/aaaa"
        tipoTeclado="number-pad"
        ajuda={ajuda}
        erro={erro ?? aviso}
        aoSair={() => {
          setSaiu(true);
          const normalizada = normalizarDataDigitada(valor);
          if (normalizada !== valor) aoMudar(normalizada);
        }}
        acessorio={
          <SeletorData
            valor={iso ? paraData(iso) : inicial}
            aoEscolher={(data) => aoMudar(dataCurta(diaLocalIso(data)))}
            minimo={minimo}
            maximo={maximo}
            rotuloAcessivel={`Escolher ${rotulo.toLowerCase()} no calendário`}
            estilo={styles.botaoCalendario}>
            <Icone nome="calendario" tamanho={18} />
          </SeletorData>
        }
      />
      {valor ? (
        <Pressable
          onPress={() => {
            setSaiu(false);
            aoMudar('');
          }}
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

/**
 * Valor do campo do navegador ("AAAA-MM-DD" ou "HH:MM") como data, mantendo da `base` a
 * parte que não muda. Enquanto o ano está sendo digitado o navegador já informa datas
 * como 0002-12-01: ano fora de 1900–2100 é tratado como incompleto, e não como uma data.
 */
function deEntradaWeb(entrada: string, modo: 'data' | 'hora', base: Date): Date | null {
  if (modo === 'hora') {
    const [h, min] = entrada.split(':').map(Number);
    const data = new Date(base);
    data.setHours(h, min, 0, 0);
    return data;
  }
  const [ano, mes, dia] = entrada.split('-').map(Number);
  if (ano < 1900 || ano > 2100) return null;
  return new Date(ano, mes - 1, dia, base.getHours(), base.getMinutes());
}

/** "HH:MM" digitado no celular como data, mantendo o dia da `base`. */
function converterHora(texto: string, base: Date): Date | null {
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
  // Alvo de toque confortável para o ícone, sem aumentar a caixa do campo.
  botaoCalendario: { padding: espaco.sm, margin: -espaco.sm, marginBottom: 0 },
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
