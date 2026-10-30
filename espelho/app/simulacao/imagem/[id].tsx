import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';

import { Cartao, Selo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { ImagemSimulada } from '@/components/ImagemSimulada';
import { useCliente, useSimulacao, useSimulacoesDoCliente } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, hora } from '@/utils/datas';

type Vista = 'resultado' | 'original' | 'lado_a_lado';

const VISTAS: { chave: Vista; rotulo: string }[] = [
  { chave: 'resultado', rotulo: 'Simulação' },
  { chave: 'original', rotulo: 'Foto original' },
  { chave: 'lado_a_lado', rotulo: 'Lado a lado' },
];

const SITUACAO = {
  processando: 'Gerando a imagem…',
  concluida: 'Pronta',
  falhou: 'Não foi possível gerar',
} as const;

/**
 * Visualização de uma simulação: o resultado, a foto que o originou, ou os dois lado a
 * lado (antes e depois).
 *
 * A foto original é a imagem de entrada guardada junto com a simulação, entregue pela
 * mesma URL assinada e temporária. As imagens são mostradas inteiras, na proporção
 * original: numa miniatura o recorte ajuda, aqui atrapalharia.
 */
export default function VerSimulacao() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const simulacao = useSimulacao(id);
  const cliente = useCliente(simulacao?.clienteId);
  const doCliente = useSimulacoesDoCliente(simulacao?.clienteId);
  const { width } = useWindowDimensions();
  const [vista, setVista] = useState<Vista>('resultado');

  // A moldura acompanha a largura disponível, com teto para não esticar no desktop.
  const larguraImagem = Math.min(width - espaco.xl * 2, 520);
  const alturaImagem = Math.round(larguraImagem * 1.25);

  if (!simulacao) {
    return (
      <Tela>
        <Cabecalho titulo="Simulação" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <Text style={textos.corpo}>Esta simulação não está mais disponível.</Text>
          <Botao titulo="Voltar" variante="texto" aoPressionar={() => router.back()} />
        </View>
      </Tela>
    );
  }

  const descricao = `Simulação de ${cliente?.nome ?? 'cliente'}: ${simulacao.parametros.estilo}, ${
    simulacao.parametros.cor
  }, gerada em ${dataCurta(simulacao.criadoEm)}`;

  return (
    <Tela>
      <Cabecalho
        titulo="Simulação"
        subtitulo={cliente ? `${cliente.nome} · ${dataCurta(simulacao.criadoEm)}` : undefined}
        aoVoltar={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        <View style={styles.abas} accessibilityRole="tablist">
          {VISTAS.map((v) => {
            const ativa = vista === v.chave;
            return (
              <Pressable
                key={v.chave}
                onPress={() => setVista(v.chave)}
                accessibilityRole="tab"
                accessibilityState={{ selected: ativa }}
                aria-selected={ativa}
                style={[styles.aba, ativa && styles.abaAtiva]}>
                <Text style={[styles.abaTexto, ativa && styles.abaTextoAtiva]}>{v.rotulo}</Text>
              </Pressable>
            );
          })}
        </View>

        {vista === 'lado_a_lado' ? (
          <View style={[styles.par, { width: larguraImagem }]}>
            {[
              {
                titulo: 'Antes',
                uri: simulacao.imgEntradaUri,
                legenda: 'foto original',
                texto: `Foto original de ${cliente?.nome ?? 'cliente'}`,
              },
              { titulo: 'Depois', uri: simulacao.imgSaidaUri, legenda: 'simulação', texto: descricao },
            ].map((lado) => (
              <View key={lado.titulo} style={styles.coluna}>
                <Text style={[textos.etiqueta, styles.tituloColuna]}>{lado.titulo}</Text>
                <ImagemSimulada
                  uri={lado.uri}
                  claro
                  ajuste="conter"
                  descricao={lado.texto}
                  legenda={lado.legenda}
                  estilo={[styles.imagem, { width: '100%', aspectRatio: 4 / 5 }]}
                />
              </View>
            ))}
          </View>
        ) : (
          <ImagemSimulada
            uri={vista === 'original' ? simulacao.imgEntradaUri : simulacao.imgSaidaUri}
            claro
            ajuste="conter"
            descricao={
              vista === 'original'
                ? `Foto original de ${cliente?.nome ?? 'cliente'} usada nesta simulação`
                : descricao
            }
            legenda={
              vista === 'original'
                ? 'foto original'
                : simulacao.status === 'processando'
                  ? 'gerando…'
                  : 'simulação'
            }
            estilo={[styles.imagem, { width: larguraImagem, height: alturaImagem }]}
          />
        )}
        {vista === 'original' && !simulacao.imgEntradaUri ? (
          <Text style={[textos.apoio, styles.aviso]}>
            A foto original não está mais guardada (as imagens deste cliente foram apagadas).
          </Text>
        ) : null}

        <View style={styles.selos}>
          <Selo texto={simulacao.parametros.estilo} tom="neutro" icone="corte" />
          <Selo texto={simulacao.parametros.cor} tom="neutro" icone="cor" />
          {simulacao.preferida ? <Selo texto="preferida" tom="acao" icone="ok" /> : null}
        </View>

        <Cartao estilo={styles.ficha}>
          <Linha
            rotulo="Gerada em"
            valor={`${dataCurta(simulacao.criadoEm)} às ${hora(simulacao.criadoEm)}`}
          />
          <Linha rotulo="Situação" valor={SITUACAO[simulacao.status]} />
          {simulacao.modeloIa ? <Linha rotulo="Modelo" valor={simulacao.modeloIa} /> : null}
          {simulacao.tempoMs ? (
            <Linha rotulo="Tempo de geração" valor={`${Math.round(simulacao.tempoMs / 1000)} segundos`} />
          ) : null}
          {simulacao.parametros.observacoes ? (
            <Linha rotulo="Observações" valor={simulacao.parametros.observacoes} />
          ) : null}
        </Cartao>

        {simulacao.status === 'falhou' && simulacao.erroCodigo ? (
          <Text style={[textos.apoio, styles.falha]}>
            A geração não concluiu. O profissional pode tentar de novo pela barra inferior.
          </Text>
        ) : null}

        {doCliente.length > 1 ? (
          <Botao
            titulo="Comparar com outra simulação"
            variante="secundaria"
            icone="comparar"
            aoPressionar={() => router.push(`/simulacao/comparar?clienteId=${simulacao.clienteId}`)}
            estilo={styles.comparar}
          />
        ) : null}
      </ScrollView>
    </Tela>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <View style={styles.linha}>
      <Text style={textos.meta}>{rotulo}</Text>
      <Text style={[textos.apoioForte, styles.valor]}>{valor}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  ausente: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espaco.md },
  conteudo: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.lg,
    paddingBottom: espaco.xxl,
    alignItems: 'center',
  },
  imagem: { borderRadius: raios.cartao, backgroundColor: cores.superficieAfundada },
  abas: {
    flexDirection: 'row',
    alignSelf: 'stretch',
    backgroundColor: cores.superficieAfundada,
    borderRadius: raios.campo,
    padding: 3,
    marginBottom: espaco.lg,
  },
  aba: {
    flex: 1,
    minHeight: 40,
    borderRadius: raios.campo - 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  abaAtiva: { backgroundColor: cores.superficie },
  abaTexto: { fontFamily: 'FamiljenGrotesk_500Medium', fontSize: 13, color: cores.textoSecundario },
  abaTextoAtiva: { fontFamily: 'FamiljenGrotesk_600SemiBold', color: cores.texto },
  par: { flexDirection: 'row', gap: espaco.md },
  coluna: { flex: 1 },
  tituloColuna: { marginBottom: espaco.xs },
  aviso: { marginTop: espaco.md, alignSelf: 'stretch' },
  selos: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: espaco.sm,
    marginTop: espaco.lg,
    alignSelf: 'stretch',
  },
  ficha: { marginTop: espaco.lg, alignSelf: 'stretch', gap: espaco.sm },
  linha: { flexDirection: 'row', justifyContent: 'space-between', gap: espaco.md },
  valor: { flexShrink: 1, textAlign: 'right' },
  falha: { marginTop: espaco.md, alignSelf: 'stretch', color: cores.erroTexto },
  comparar: { marginTop: espaco.lg, alignSelf: 'stretch' },
});
