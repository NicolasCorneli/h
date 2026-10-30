import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Selo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { ImagemSimulada } from '@/components/ImagemSimulada';
import { useRascunho } from '@/data/rascunho';
import { useSimulacoesDoCliente, useStore } from '@/data/store';
import { Icone } from '@/components/Icone';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, fontes, raios } from '@/theme/tokens';
import { rotuloCor, rotuloCorte } from '@/utils/pedido';

/**
 * T7 — antes/depois, parâmetros usados e o aviso de aproximação visual (seção 5.11).
 *
 * A simulação **já está salva** quando esta tela abre: ela foi criada pelo servidor no
 * `POST /simulacoes` e guardada com as duas imagens no storage. Antes da integração era
 * aqui que o registro nascia, e por isso existia um botão "Salvar no histórico"; agora o
 * passo que falta é o do negócio — registrar o atendimento executado.
 */
export default function Resultado() {
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const [verInstrucao, setVerInstrucao] = useState(false);
  const { avisar } = useFeedback();
  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);
  const simulacoes = useSimulacoesDoCliente(rascunho.clienteId ?? undefined);
  const simulacao = simulacoes.find((s) => s.id === rascunho.simulacaoId) ?? null;
  const segundos = Math.max(1, Math.round((simulacao?.tempoMs ?? 0) / 1000));
  const escolhas = {
    corte: rascunho.corte,
    manterCorte: rascunho.manterCorte,
    cor: rascunho.cor,
    manterCor: rascunho.manterCor,
  };

  /** Volta às escolhas, que continuam preenchidas, para ajustar e gerar outra. */
  function refazer() {
    atualizar({ simulacaoId: null, chaveEnvio: null, falhaEnvio: null });
    router.dismissTo('/simulacao/parametros');
  }

  function registrarAtendimento() {
    if (!rascunho.clienteId || !simulacao) {
      avisar('Simulação não encontrada', 'erro');
      return;
    }
    router.push(
      `/atendimento/novo?clienteId=${rascunho.clienteId}&simulacaoId=${simulacao.id}`
    );
  }

  return (
    <Tela>
      <Cabecalho
        titulo="Resultado"
        subtitulo={`${cliente?.nome ?? 'Simulação'} · gerado em ${segundos}s`}
        aoVoltar={refazer}
        comLinha={false}
        direita={
          cliente ? (
            <Botao
              titulo="Comparar"
              variante="texto"
              larguraTotal={false}
              aoPressionar={() => router.push(`/simulacao/comparar?clienteId=${cliente.id}`)}
            />
          ) : null
        }
      />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        <View style={styles.par}>
          <View style={styles.coluna}>
            <Text style={[textos.etiqueta, styles.rotulo]}>Antes</Text>
            <ImagemSimulada
              uri={simulacao?.imgEntradaUri ?? rascunho.foto?.uri}
              legenda="foto original"
              estilo={styles.imagem}
            />
          </View>
          <View style={styles.coluna}>
            <Text style={[textos.etiqueta, styles.rotuloDepois]}>Simulação</Text>
            <ImagemSimulada
              uri={simulacao?.imgSaidaUri}
              claro
              legenda="imagem gerada"
              estilo={[styles.imagem, styles.imagemDestaque]}
            />
          </View>
        </View>

        <View style={styles.pedido}>
          <View style={styles.linhaPedido}>
            <Icone nome="corte" tamanho={14} cor={cores.textoTerciario} />
            <Text style={[textos.apoio, styles.flex]}>
              <Text style={styles.rotuloPedido}>Corte: </Text>
              {simulacao?.parametros.estilo ?? rotuloCorte(escolhas)}
            </Text>
          </View>
          <View style={styles.linhaPedido}>
            <Icone nome="cor" tamanho={14} cor={cores.textoTerciario} />
            <Text style={[textos.apoio, styles.flex]}>
              <Text style={styles.rotuloPedido}>Cor: </Text>
              {simulacao?.parametros.cor ?? rotuloCor(escolhas)}
            </Text>
          </View>
        </View>

        <View style={styles.chips}>
          {simulacao ? <Selo texto={simulacao.modeloIa} tom="neutro" /> : null}
        </View>

        {simulacao?.instrucaoIa ? (
          <View style={styles.instrucaoBloco}>
            <Pressable
              onPress={() => setVerInstrucao((v) => !v)}
              accessibilityRole="button"
              accessibilityState={{ expanded: verInstrucao }}
              accessibilityLabel={verInstrucao ? 'Esconder o que foi pedido ao modelo' : 'Ver o que foi pedido ao modelo'}
              style={styles.alternar}>
              <Text style={textos.link}>
                {verInstrucao ? 'Esconder o que foi pedido ao modelo' : 'Ver o que foi pedido ao modelo'}
              </Text>
              <Icone nome="chevron" tamanho={14} cor={cores.acaoTexto} />
            </Pressable>
            {verInstrucao ? (
              <Text style={styles.instrucao} selectable>
                {simulacao.instrucaoIa}
              </Text>
            ) : null}
          </View>
        ) : null}

        <Aviso
          tom="alerta"
          titulo="Isto é uma aproximação visual"
          texto="Textura real do fio, volume e histórico químico podem mudar o resultado executado. Use a imagem para conversar, não como promessa."
        />

        <Text style={[textos.meta, styles.guardada]}>
          A simulação já está guardada no histórico de {cliente?.nome.split(' ')[0] ?? 'cliente'}.
          As imagens abrem por link temporário e podem ser excluídas a qualquer momento.
        </Text>
      </ScrollView>

      <View style={styles.rodape}>
        <Botao
          titulo="Refazer"
          variante="secundaria"
          icone="trocarCamera"
          larguraTotal={false}
          aoPressionar={refazer}
          rotuloAcessivel="Refazer: voltar às escolhas, ajustar e gerar de novo"
        />
        <Botao
          titulo="Registrar atendimento"
          icone="registrar"
          aoPressionar={registrarAtendimento}
          estilo={styles.salvar}
        />
      </View>
    </Tela>
  );
}

const styles = StyleSheet.create({
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.sm, paddingBottom: espaco.lg },
  par: { flexDirection: 'row', gap: espaco.sm },
  coluna: { flex: 1 },
  rotulo: { marginBottom: espaco.sm },
  rotuloDepois: { marginBottom: espaco.sm, color: cores.acaoTexto },
  imagem: { height: 250, borderWidth: 1, borderColor: cores.borda },
  imagemDestaque: { borderWidth: 2, borderColor: cores.acao },
  flex: { flex: 1 },
  pedido: { gap: espaco.xs, marginTop: espaco.lg },
  linhaPedido: { flexDirection: 'row', gap: espaco.sm, alignItems: 'flex-start' },
  rotuloPedido: { fontFamily: fontes.sansSemi, color: cores.texto },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.sm, marginVertical: espaco.md },
  instrucaoBloco: { marginBottom: espaco.md },
  alternar: { flexDirection: 'row', alignItems: 'center', gap: espaco.xs, minHeight: ALVO_TOQUE },
  instrucao: {
    fontFamily: fontes.mono,
    fontSize: 12,
    lineHeight: 18,
    color: cores.textoSecundario,
    backgroundColor: cores.superficieSuave,
    borderRadius: raios.campo,
    padding: espaco.md,
  },
  rodape: {
    flexDirection: 'row',
    gap: espaco.sm,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
  },
  salvar: { flex: 1 },
  guardada: { marginTop: espaco.md },
});
