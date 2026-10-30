import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { useIsFocused, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BotaoIcone } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { useFeedback } from '@/components/Feedback';
import { Icone } from '@/components/Icone';
import { useRascunho } from '@/data/rascunho';
import { useAvaliacaoCaptura, useResumoConsentimento, useStore } from '@/data/store';
import { rotuloFormaObtencao } from '@/services/consentService';
import { validarFoto, type FotoCapturada } from '@/services/simulacaoService';
import { useEnquadramento } from '@/services/enquadramento';
import { useModoDemo } from '@/services/modoDemo';
import { textosEscuros } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta } from '@/utils/datas';

/**
 * T5 — captura com guia de enquadramento e pré-checagem antes do envio.
 *
 * A câmera só monta quando o consentimento do cliente está válido, e **quem decide é o
 * servidor**: `cliente.consentimento.bloqueio` chega junto com o cliente, e o
 * `POST /simulacoes` recusa com 403 de todo modo. A verificação aqui evita abrir a
 * câmera para nada; ela não é o controle de acesso.
 */
export default function Captura() {
  const modoDemo = useModoDemo();
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const { avisar } = useFeedback();
  const [permissao, pedirPermissao] = useCameraPermissions();
  const [frontal, setFrontal] = useState(true);
  const [capturando, setCapturando] = useState(false);
  const cameraRef = useRef<CameraView>(null);
  const focada = useIsFocused();

  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);
  const avaliacao = useAvaliacaoCaptura(rascunho.clienteId);
  const resumo = useResumoConsentimento(rascunho.clienteId);
  // Conferência ao vivo do enquadramento: só com a câmera liberada, o cliente autorizado,
  // fora do momento da captura e com esta tela à vista. A pilha mantém a tela montada
  // depois que a foto segue para "Estilo e cor"; sem a condição do foco, ela continuava
  // tirando miniaturas e chamando o servidor enquanto o profissional preenchia o pedido.
  const enquadramento = useEnquadramento(
    cameraRef,
    rascunho.clienteId,
    focada && !!permissao?.granted && avaliacao.permitida && !capturando
  );

  function seguir(foto: FotoCapturada, demoRecusarFoto = false) {
    // Pré-checagem local: o que dá para medir no aparelho, para não subir em vão.
    const problemas = demoRecusarFoto ? [] : validarFoto(foto);
    atualizar({ foto, problemas, demoRecusarFoto, simulacaoId: null });
    router.push(problemas.length > 0 ? '/simulacao/recusada' : '/simulacao/parametros');
  }

  async function fotografar() {
    setCapturando(true);
    try {
      const foto = await cameraRef.current?.takePictureAsync({ quality: 0.85 });
      if (foto) seguir({ uri: foto.uri, width: foto.width, height: foto.height });
    } catch {
      avisar('Não foi possível capturar a foto', 'erro');
    } finally {
      setCapturando(false);
    }
  }

  async function escolherDaGaleria() {
    const autorizacao = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!autorizacao.granted) {
      avisar('Acesso à galeria não liberado', 'erro');
      return;
    }
    const resultado = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.85 });
    if (resultado.canceled) return;
    const escolhida = resultado.assets[0];
    seguir({ uri: escolhida.uri, width: escolhida.width ?? 0, height: escolhida.height ?? 0 });
  }

  /**
   * Reproduz o caminho de recusa sem depender de uma foto realmente ruim.
   *
   * Não inventa a recusa: a marca viaja no envio e é o **servidor** que devolve 422 com
   * a lista de problemas, como faria com uma foto de verdade. Só funciona com o servidor
   * em modo demonstração.
   */
  async function simularFotoRuim() {
    setCapturando(true);
    try {
      const foto = await cameraRef.current?.takePictureAsync({ quality: 0.85 });
      seguir(
        foto
          ? { uri: foto.uri, width: foto.width, height: foto.height }
          : { uri: rascunho.foto?.uri ?? '', width: 800, height: 1000 },
        true
      );
    } catch {
      avisar('Não foi possível capturar a foto', 'erro');
    } finally {
      setCapturando(false);
    }
  }

  if (!avaliacao.permitida) {
    return (
      <SafeAreaView style={styles.tela} edges={['top', 'bottom']}>
        <View style={styles.topo}>
          <BotaoIcone icone="fechar" aoPressionar={() => router.back()} rotuloAcessivel="Fechar" escuro />
          <Text style={styles.nomeCliente}>{cliente?.nome ?? 'Sem cliente'}</Text>
          <View style={styles.espaco} />
        </View>

        <View style={styles.bloqueio}>
          <View style={styles.cadeado}>
            <Icone nome="cadeado" tamanho={22} cor={cores.escuroTexto} />
          </View>
          <Text style={[textosEscuros.display, styles.bloqueioTitulo]} accessibilityRole="header">
            {avaliacao.titulo}
          </Text>
          <Text style={[textosEscuros.corpo, styles.bloqueioTexto]}>{avaliacao.descricao}</Text>

          {avaliacao.acao === 'apresentar_termo' && cliente ? (
            <>
              <Botao
                titulo="Apresentar termo ao cliente"
                variante="secundaria"
                icone="documento"
                aoPressionar={() => router.replace(`/consentimento/${cliente.id}?retorno=captura`)}
              />
              <Botao
                titulo="Voltar ao perfil do cliente"
                variante="texto"
                aoPressionar={() => router.replace(`/cliente/${cliente.id}`)}
                estilo={styles.bloqueioSecundario}
              />
            </>
          ) : (
            <Botao
              titulo="Escolher cliente"
              variante="secundaria"
              icone="clientes"
              aoPressionar={() => router.replace('/simulacao/cliente')}
            />
          )}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.tela} edges={['top', 'bottom']}>
      <View style={styles.topo}>
        <BotaoIcone
          icone="fechar"
          aoPressionar={() => router.back()}
          rotuloAcessivel="Fechar câmera"
          escuro
        />
        <View style={styles.identificacao}>
          <Text style={styles.etapa}>Etapa 2 de 3</Text>
          <Text style={styles.nomeCliente}>{cliente?.nome}</Text>
        </View>
        <BotaoIcone
          icone="trocarCamera"
          aoPressionar={() => setFrontal((v) => !v)}
          rotuloAcessivel="Alternar entre câmera frontal e traseira"
          escuro
        />
      </View>

      <View style={styles.visor}>
        {permissao?.granted ? (
          <CameraView
            ref={cameraRef}
            style={StyleSheet.absoluteFill}
            facing={frontal ? 'front' : 'back'}
            // As fotos pequenas da conferência do enquadramento não piscam a tela.
            animateShutter={false}
          />
        ) : (
          <View style={styles.semPermissao}>
            <Icone nome="camera" tamanho={28} cor={cores.escuroTextoApoio} />
            <Text style={[textosEscuros.secao, styles.semPermissaoTitulo]}>Câmera não liberada</Text>
            <Text style={[textosEscuros.corpo, styles.semPermissaoTexto]}>
              Libere a câmera para fotografar o cliente, ou use uma foto que já esteja na galeria.
            </Text>
            <Botao
              titulo="Liberar câmera"
              variante="secundaria"
              tamanho="medio"
              larguraTotal={false}
              aoPressionar={() => pedirPermissao()}
              estilo={styles.botaoPermissao}
            />
          </View>
        )}
        <View style={[styles.guia, { pointerEvents: 'none' }]} />
        {permissao?.granted ? (
          <View style={[styles.dicas, { pointerEvents: 'none' }]} accessibilityLiveRegion="polite">
            {enquadramento === 'no_guia' ? (
              <View style={[styles.dica, styles.dicaOk]}>
                <Icone nome="ok" tamanho={13} cor="#EFF7F2" />
                <Text style={styles.dicaTextoOk}>Rosto dentro do guia</Text>
              </View>
            ) : (
              <View style={[styles.dica, styles.dicaAtencao]}>
                <Icone nome="info" tamanho={13} cor="#FBF5E6" />
                <Text style={styles.dicaTextoAtencao}>Enquadre o rosto no guia para um melhor resultado</Text>
              </View>
            )}
          </View>
        ) : null}
      </View>

      <View style={styles.rodape}>
        <View style={styles.consentimento}>
          <Icone nome="okCirculo" tamanho={16} cor="#5BC79D" />
          <Text style={styles.consentimentoTexto}>
            {resumo.registro
              ? `${cliente?.nome.split(' ')[0]} autorizou em ${dataCurta(
                  resumo.registro.registradoEm
                )} · ${rotuloFormaObtencao(resumo.registro.formaObtencao)} · termo ${
                  resumo.registro.versaoTermo
                }`
              : 'Consentimento registrado para este cliente.'}
          </Text>
        </View>

        <View style={styles.controles}>
          <Pressable
            onPress={escolherDaGaleria}
            accessibilityRole="button"
            accessibilityLabel="Escolher foto da galeria"
            style={({ pressed }) => [styles.lateral, pressed && styles.pressionado]}>
            <Icone nome="galeria" tamanho={20} cor={cores.escuroTextoSecundario} />
            <Text style={styles.lateralTexto}>Galeria</Text>
          </Pressable>

          <Pressable
            onPress={fotografar}
            disabled={!permissao?.granted || capturando}
            accessibilityRole="button"
            accessibilityLabel="Capturar foto"
            accessibilityState={{ disabled: !permissao?.granted, busy: capturando }}
            style={({ pressed }) => [
              styles.obturador,
              (!permissao?.granted || capturando) && styles.obturadorDesativado,
              pressed && styles.pressionado,
            ]}>
            <View style={styles.obturadorInterno} />
          </Pressable>

          {modoDemo ? (
            <Pressable
              onPress={() => void simularFotoRuim()}
              accessibilityRole="button"
              accessibilityLabel="Demonstrar a recusa de uma foto de baixa qualidade"
              style={({ pressed }) => [styles.lateral, pressed && styles.pressionado]}>
              <Icone nome="alerta" tamanho={20} cor={cores.escuroTextoApoio} />
              <Text style={[styles.lateralTexto, styles.lateralDemo]}>Foto ruim</Text>
            </Pressable>
          ) : (
            // Mesmo espaço do atalho, para o botão de fotografar continuar no centro.
            <View style={styles.lateral} />
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cores.camera },
  topo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.sm,
    gap: espaco.md,
  },
  identificacao: { alignItems: 'center' },
  etapa: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 11,
    color: cores.escuroTextoApoio,
  },
  nomeCliente: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 15,
    color: cores.escuroTexto,
  },
  espaco: { width: 44 },
  visor: {
    flex: 1,
    marginVertical: espaco.lg,
    backgroundColor: '#15110F',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  semPermissao: { paddingHorizontal: espaco.xxxl, alignItems: 'center', gap: espaco.sm },
  semPermissaoTitulo: { marginTop: espaco.sm },
  semPermissaoTexto: { textAlign: 'center' },
  // O Botao estreito se alinha à esquerda por padrão; aqui fica no centro, com o texto.
  botaoPermissao: { marginTop: espaco.md, alignSelf: 'center' },
  guia: {
    width: 220,
    height: 296,
    borderRadius: 140,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: 'rgba(243,237,231,0.6)',
  },
  dicas: {
    position: 'absolute',
    left: espaco.xl,
    right: espaco.xl,
    bottom: espaco.xl,
    flexDirection: 'row',
    gap: espaco.sm,
    justifyContent: 'center',
  },
  dica: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.sm,
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.sm,
    borderRadius: raios.campo,
  },
  dicaOk: { backgroundColor: 'rgba(31,90,67,0.94)' },
  dicaAtencao: { backgroundColor: 'rgba(94,74,18,0.94)' },
  dicaTextoOk: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 12, color: '#EFF7F2' },
  dicaTextoAtencao: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 12,
    color: '#FBF5E6',
    flexShrink: 1,
  },
  rodape: { paddingHorizontal: espaco.xl, paddingBottom: espaco.md },
  consentimento: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    marginBottom: espaco.lg,
  },
  consentimentoTexto: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_400Regular',
    fontSize: 13,
    lineHeight: 18,
    color: cores.escuroTextoSecundario,
  },
  controles: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  lateral: { width: 76, alignItems: 'center', gap: espaco.xs, minHeight: 60, justifyContent: 'center' },
  lateralTexto: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 12,
    color: cores.escuroTextoSecundario,
  },
  lateralDemo: { color: cores.escuroTextoApoio },
  obturador: {
    width: 78,
    height: 78,
    borderRadius: 39,
    borderWidth: 3,
    borderColor: 'rgba(243,237,231,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  obturadorInterno: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: cores.escuroTexto,
  },
  obturadorDesativado: { opacity: 0.4 },
  bloqueio: { flex: 1, justifyContent: 'center', paddingHorizontal: espaco.xxl, paddingBottom: espaco.xxxl },
  cadeado: {
    width: 52,
    height: 52,
    borderRadius: raios.cartao,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espaco.xl,
  },
  bloqueioTitulo: { marginBottom: espaco.md },
  bloqueioTexto: { marginBottom: espaco.xxl },
  bloqueioSecundario: { marginTop: espaco.xs },
  pressionado: { opacity: 0.85 },
});
