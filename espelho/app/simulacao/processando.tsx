import * as Crypto from 'expo-crypto';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icone } from '@/components/Icone';
import { useRascunho } from '@/data/rascunho';
import { useStore } from '@/data/store';
import { useFeedback } from '@/components/Feedback';
import { ErroApi, prepararFotoParaEnvio } from '@/services/api';
import { reduzirParaEnvio } from '@/services/imagemLocal';
import { problemasDoErro } from '@/services/simulacaoService';
import { textosEscuros } from '@/theme/textos';
import { cores, espaco, fontes, raios } from '@/theme/tokens';

// Na web não há módulo de animação nativo: pedir o driver nativo gera aviso a cada
// animação e cai para JS de qualquer forma. No aparelho, o driver nativo fica.
const DRIVER_NATIVO = Platform.OS !== 'web';

const ETAPAS = [
  { limite: 0, texto: 'Foto e pedido enviados com segurança' },
  { limite: 1, texto: 'Pedido aceito pelo serviço de simulação' },
  { limite: 2, texto: 'Aplicando o corte e a cor pedidos' },
];

/** Lado maior das fotos enviadas: o modelo gera por volta de 1 megapixel. */
const LADO_ENVIO = 1536;

/** Erros que pedem correção no pedido: a tela volta para "Estilo e cor" com o motivo. */
const ERROS_DO_PEDIDO = new Set([
  'descricao_invalida',
  'descricao_longa',
  'descricao_livre_indisponivel',
  'corte_vazio',
  'cor_vazia',
  'pedido_vazio',
  'genero_invalido',
  'chave_reutilizada',
]);

/**
 * Espera da inferência (RNF02).
 *
 * Aqui acontece o envio de verdade: a foto sobe para o servidor, que valida, guarda no
 * storage, confere o consentimento e aciona o provedor de IA. A resposta é 202 com a
 * simulação em `processando`, e esta tela consulta o estado até concluir ou falhar.
 *
 * O progresso mostrado é uma estimativa de tempo: o provedor não informa percentual.
 * Por isso a barra acompanha o relógio e as etapas avançam conforme as consultas, em vez
 * de fingir precisão.
 */
export default function Processando() {
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { acoes } = useStore();
  const { avisar } = useFeedback();
  const [consultas, setConsultas] = useState(0);
  const [segundos, setSegundos] = useState(0);
  const giro = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animacao = Animated.loop(
      Animated.timing(giro, {
        toValue: 1,
        duration: 1100,
        easing: Easing.linear,
        useNativeDriver: DRIVER_NATIVO,
      })
    );
    animacao.start();
    return () => animacao.stop();
  }, [giro]);

  useEffect(() => {
    const relogio = setInterval(() => setSegundos((valor) => valor + 1), 1000);
    return () => clearInterval(relogio);
  }, []);

  useEffect(() => {
    if (!rascunho.foto || !rascunho.clienteId) {
      router.replace('/simulacao/captura');
      return;
    }

    let ativo = true;

    // A mesma chave em uma nova visita a esta tela (voltar e tocar em "Gerar" de novo)
    // devolve a simulação já criada, sem pagar outra geração.
    const chaveEnvio = rascunho.chaveEnvio ?? Crypto.randomUUID();
    atualizar({ chaveEnvio, falhaEnvio: null });

    (async () => {
      try {
        const original = rascunho.foto!;
        const foto = await prepararFotoParaEnvio(
          await reduzirParaEnvio(original.uri, original.width, original.height, LADO_ENVIO)
        );
        const criada = await acoes.criarSimulacao({
          clienteId: rascunho.clienteId!,
          corte: rascunho.corte,
          manterCorte: rascunho.manterCorte,
          cor: rascunho.cor,
          manterCor: rascunho.manterCor,
          genero: rascunho.genero,
          observacoes: rascunho.observacoes,
          foto,
          chaveEnvio,
          demoRecusarFoto: rascunho.demoRecusarFoto,
          demoFalharIa: rascunho.demoFalharIa,
        });
        if (!ativo) return;
        atualizar({ simulacaoId: criada.id, chaveEnvio });
        setConsultas(1);

        const final = await acoes.acompanharSimulacao(criada.id);
        if (!ativo) return;
        setConsultas(3);
        // Tentativa encerrada: a próxima, mesmo com o mesmo pedido, é uma geração nova.
        atualizar({ chaveEnvio: null });
        router.replace(
          final.status === 'concluida' ? '/simulacao/resultado' : '/simulacao/indisponivel'
        );
      } catch (falha) {
        if (!ativo) return;
        const apiErro = falha instanceof ErroApi ? falha : null;

        // O pedido precisa de correção: volta para a etapa de escolhas, com o motivo.
        if (apiErro && ERROS_DO_PEDIDO.has(apiErro.codigo)) {
          atualizar({ chaveEnvio: null });
          avisar(apiErro.message, 'erro');
          router.dismissTo('/simulacao/parametros');
          return;
        }

        // Foto recusada pelo servidor: a lista de problemas dele é a que a tela mostra.
        if (apiErro?.codigo === 'foto_recusada') {
          atualizar({ problemas: problemasDoErro(apiErro.detalhes) });
          router.replace('/simulacao/recusada');
          return;
        }

        // Consentimento inválido: volta ao fluxo do cliente, que explica o bloqueio.
        if (apiErro?.codigo === 'consentimento_invalido') {
          router.replace(
            rascunho.clienteId ? `/cliente/${rascunho.clienteId}` : '/simulacao/cliente'
          );
          return;
        }

        // Cota, credencial, conexão, provedor fora do ar: a tela de falha explica, e as
        // escolhas continuam no rascunho para tentar de novo. Sem conexão, a chave fica:
        // se o servidor chegou a receber, a nova tentativa devolve a mesma simulação.
        atualizar({
          falhaEnvio: {
            codigo: apiErro?.codigo ?? 'desconhecido',
            mensagem: apiErro?.message ?? 'Não foi possível enviar a simulação.',
          },
          ...(apiErro?.deConexao ? {} : { chaveEnvio: null }),
        });
        router.replace('/simulacao/indisponivel');
      }
    })();

    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Estimativa: a maioria das gerações conclui em menos de 30 segundos.
  const percentual = Math.min(95, Math.round((segundos / 30) * 100));

  return (
    <SafeAreaView style={styles.tela} edges={['top', 'bottom']}>
      <View style={styles.centro}>
        <Animated.View
          style={[
            styles.spinner,
            {
              transform: [
                {
                  rotate: giro.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] }),
                },
              ],
            },
          ]}
        />
        <Text style={[textosEscuros.display, styles.titulo]} accessibilityRole="header">
          Gerando a simulação
        </Text>
        <Text style={[textosEscuros.corpo, styles.subtitulo]}>
          A foto foi enviada ao serviço de simulação. Leva alguns segundos.
        </Text>
        <View
          style={styles.trilho}
          accessibilityRole="progressbar"
          accessibilityValue={{ now: percentual, min: 0, max: 100 }}>
          <View style={[styles.barra, { width: `${percentual}%` }]} />
        </View>
        <Text style={styles.percentual}>{segundos}s</Text>
      </View>

      <View style={styles.etapas}>
        {ETAPAS.map((etapa) => (
          <View key={etapa.texto} style={styles.etapa}>
            <Icone
              nome={consultas > etapa.limite ? 'okCirculo' : 'relogio'}
              tamanho={16}
              cor={consultas > etapa.limite ? '#5BC79D' : cores.escuroTextoTenue}
            />
            <Text style={[styles.etapaTexto, consultas > etapa.limite && styles.etapaAtiva]}>
              {etapa.texto}
            </Text>
          </View>
        ))}
      </View>

      <Pressable
        onPress={() => {
          // A geração continua no servidor. A chave fica: "Tentar novamente" retoma a
          // mesma simulação em vez de pagar outra.
          atualizar({
            falhaEnvio: {
              codigo: 'parou_de_esperar',
              mensagem: 'Você parou de esperar.',
            },
          });
          router.replace('/simulacao/indisponivel');
        }}
        accessibilityRole="button"
        accessibilityLabel="Parar de esperar e voltar"
        style={styles.demo}>
        <Text style={styles.demoTexto}>Está demorando demais? Parar de esperar</Text>
      </Pressable>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  tela: {
    flex: 1,
    backgroundColor: cores.tinta,
    paddingHorizontal: espaco.xxl,
    paddingBottom: espaco.xl,
  },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  spinner: {
    width: 112,
    height: 112,
    borderRadius: 56,
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.12)',
    borderTopColor: cores.acaoDecorativa,
    marginBottom: espaco.xxl,
  },
  titulo: { textAlign: 'center' },
  subtitulo: { marginTop: espaco.sm, maxWidth: 280, textAlign: 'center' },
  trilho: {
    width: 190,
    height: 6,
    borderRadius: raios.pilula,
    backgroundColor: 'rgba(255,255,255,0.14)',
    marginTop: espaco.xxl,
    overflow: 'hidden',
  },
  barra: { height: '100%', borderRadius: raios.pilula, backgroundColor: cores.acaoDecorativa },
  percentual: {
    fontFamily: fontes.mono,
    fontSize: 13,
    color: cores.escuroTextoSecundario,
    marginTop: espaco.md,
  },
  etapas: { gap: espaco.md, paddingBottom: espaco.xl },
  etapa: { flexDirection: 'row', gap: espaco.md, alignItems: 'center' },
  etapaTexto: { fontFamily: fontes.sansMedio, fontSize: 14, color: cores.escuroTextoTenue },
  etapaAtiva: { color: cores.escuroTexto },
  demo: {
    alignItems: 'center',
    paddingVertical: espaco.md,
    minHeight: 44,
    justifyContent: 'center',
  },
  demoTexto: { fontFamily: fontes.sansMedio, fontSize: 13, color: cores.escuroTextoApoio },
});
