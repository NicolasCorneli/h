import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Cartao, Etiqueta, Selo, Tela } from '@/components/Basicos';
import { Cabecalho } from '@/components/Cabecalho';
import { EstadoVazio } from '@/components/EstadoVazio';
import { Icone } from '@/components/Icone';
import { ImagemSimulada } from '@/components/ImagemSimulada';
import { useCliente, useSimulacoesDoCliente } from '@/data/store';
import type { Simulacao } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, raios } from '@/theme/tokens';
import { diaMes } from '@/utils/datas';
import { escolherParaComparar, type Posicoes } from '@/utils/comparacao';

/**
 * RF07: duas simulações do mesmo cliente lado a lado.
 *
 * A escolha da preferida fica no perfil do cliente, em cada simulação; aqui ela só aparece
 * como selo. Com mais de duas, uma grade de miniaturas escolhe quais comparar: tocar
 * inclui, tocar de novo tira, e cada marcada diz o lado em que está.
 */
export default function Comparar() {
  const { clienteId } = useLocalSearchParams<{ clienteId: string }>();
  const router = useRouter();
  const cliente = useCliente(clienteId);
  const simulacoes = useSimulacoesDoCliente(clienteId);
  // Nulo até a primeira escolha: valem as duas primeiras da lista (a preferida e a mais
  // recente). Cada lado é uma posição fixa: tirar a da esquerda não muda a da direita.
  const [escolha, setEscolha] = useState<Posicoes | null>(null);

  if (!cliente || simulacoes.length < 2) {
    const quantas = simulacoes.length;
    return (
      <Tela>
        <Cabecalho titulo="Comparar simulações" aoVoltar={() => router.back()} />
        <EstadoVazio
          icone="comparar"
          titulo="Ainda não há o que comparar"
          texto={
            quantas === 0
              ? 'Este cliente ainda não tem simulações salvas. Gere duas pelo botão de simulação, na barra inferior, para poder compará-las.'
              : 'Há apenas uma simulação salva. Gere mais uma pelo botão de simulação, na barra inferior, e as duas aparecerão aqui lado a lado.'
          }
          acao={{
            titulo: 'Voltar ao perfil',
            // Aberta direto pelo endereço (ou recarregada), não há tela anterior: vai ao perfil.
            aoPressionar: () => (router.canGoBack() ? router.back() : router.replace(`/cliente/${clienteId}`)),
          }}
        />
      </Tela>
    );
  }

  const existe = (id: string | null) => (id && simulacoes.some((s) => s.id === id) ? id : null);
  // Uma simulação excluída enquanto a tela estava aberta deixa o lado dela vago.
  const posicoes: Posicoes = escolha
    ? { esquerda: existe(escolha.esquerda), direita: existe(escolha.direita) }
    : { esquerda: simulacoes[0].id, direita: simulacoes[1].id };
  const esquerda = simulacoes.find((s) => s.id === posicoes.esquerda) ?? null;
  const direita = simulacoes.find((s) => s.id === posicoes.direita) ?? null;
  const lado = (id: string) =>
    id === posicoes.esquerda ? 'à esquerda' : id === posicoes.direita ? 'à direita' : null;

  const cartao = (simulacao: Simulacao | null, rotulo: string) =>
    simulacao ? (
      <View style={styles.coluna}>
        <Etiqueta estilo={styles.rotuloColuna}>{rotulo}</Etiqueta>
        <ImagemSimulada
          uri={simulacao.imgSaidaUri}
          claro
          ajuste="conter"
          descricao={`Simulação de ${diaMes(simulacao.criadoEm)}: ${simulacao.parametros.estilo}, ${simulacao.parametros.cor}`}
          legenda={`simulação ${diaMes(simulacao.criadoEm)}`}
          estilo={styles.imagem}
        />
        <Cartao estilo={styles.ficha}>
          <Text style={textos.corpoForte} numberOfLines={2}>
            {simulacao.parametros.cor}
          </Text>
          <Text style={textos.apoio} numberOfLines={2}>
            {simulacao.parametros.estilo}
          </Text>
          <Text style={textos.meta}>
            {diaMes(simulacao.criadoEm)}
            {simulacao.tempoMs ? ` · ${Math.round(simulacao.tempoMs / 1000)}s` : ''}
          </Text>
          {simulacao.preferida ? <Selo texto="preferida" tom="acao" icone="ok" /> : null}
        </Cartao>
      </View>
    ) : (
      <View style={styles.coluna}>
        <Etiqueta estilo={styles.rotuloColuna}>{rotulo}</Etiqueta>
        <View style={styles.vaga}>
          <Icone nome="comparar" tamanho={20} cor={cores.textoApoio} />
          <Text style={[textos.apoio, styles.vagaTexto]}>Toque numa simulação abaixo para colocá-la aqui.</Text>
        </View>
      </View>
    );

  return (
    <Tela>
      <Cabecalho
        titulo="Comparar simulações"
        subtitulo={`${cliente.nome} · ${simulacoes.length} salvas`}
        aoVoltar={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        <View style={styles.par}>
          {cartao(esquerda, 'À esquerda')}
          {cartao(direita, 'À direita')}
        </View>

        {simulacoes.length > 2 ? (
          <View style={styles.seletor}>
            <Text style={textos.secao} accessibilityRole="header">
              Escolha as duas para comparar
            </Text>
            <Text style={textos.apoio}>
              Toque numa simulação para incluí-la e toque de novo para tirar. Com as duas
              posições ocupadas, a nova entra no lugar da direita.
            </Text>
            <View style={styles.grade}>
              {simulacoes.map((s) => {
                const onde = lado(s.id);
                return (
                  <Pressable
                    key={s.id}
                    onPress={() => setEscolha(escolherParaComparar(posicoes, s.id))}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: onde !== null }}
                    // O `accessibilityState` não chega ao HTML na web; o atributo ARIA chega.
                    aria-checked={onde !== null}
                    accessibilityLabel={`Simulação de ${diaMes(s.criadoEm)}, ${s.parametros.cor}${
                      onde ? `, comparando ${onde}` : ''
                    }`}
                    style={({ pressed }) => [
                      styles.opcao,
                      onde !== null && styles.opcaoMarcada,
                      pressed && styles.pressionado,
                    ]}>
                    <View>
                      <ImagemSimulada uri={s.imgSaidaUri} claro estilo={styles.opcaoImagem} raio={raios.campo} />
                      <View style={[styles.marca, onde !== null && styles.marcaAtiva]}>
                        {onde !== null ? <Icone nome="ok" tamanho={14} cor="#FFFFFF" /> : null}
                      </View>
                    </View>
                    <Text style={textos.meta}>{diaMes(s.criadoEm)}</Text>
                    <Text style={textos.apoioForte} numberOfLines={1}>
                      {s.parametros.cor}
                    </Text>
                    {onde ? <Selo texto={onde} tom="acao" /> : null}
                  </Pressable>
                );
              })}
            </View>
          </View>
        ) : null}
      </ScrollView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxl },
  par: { flexDirection: 'row', gap: espaco.md },
  coluna: { flex: 1 },
  rotuloColuna: { marginBottom: espaco.sm },
  // Proporção em vez de altura fixa: nas duas colunas do celular a imagem acompanha a
  // largura disponível, e com `conter` nenhuma parte do rosto é cortada.
  imagem: {
    aspectRatio: 3 / 4,
    minHeight: 180,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.superficieAfundada,
  },
  ficha: { marginTop: espaco.sm, gap: espaco.xs, padding: espaco.md },
  vaga: {
    aspectRatio: 3 / 4,
    minHeight: 180,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: cores.bordaForte,
    borderRadius: raios.cartao,
    alignItems: 'center',
    justifyContent: 'center',
    gap: espaco.sm,
    padding: espaco.md,
  },
  vagaTexto: { textAlign: 'center' },
  seletor: { marginTop: espaco.xl, gap: espaco.sm },
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.md, marginTop: espaco.sm },
  opcao: {
    width: 100,
    gap: espaco.xs,
    padding: espaco.xs,
    borderRadius: raios.cartao,
    borderWidth: 2,
    borderColor: 'transparent',
    minHeight: ALVO_TOQUE,
  },
  opcaoMarcada: { borderColor: cores.acao, backgroundColor: cores.superficie },
  opcaoImagem: { height: 112 },
  marca: {
    position: 'absolute',
    top: espaco.xs,
    right: espaco.xs,
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#FFFFFF',
    backgroundColor: 'rgba(27, 23, 20, 0.35)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  marcaAtiva: { backgroundColor: cores.acao, borderColor: cores.acao },
  pressionado: { opacity: 0.85 },
});
