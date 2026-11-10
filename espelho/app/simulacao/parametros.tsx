import { useRouter } from 'expo-router';
import { Children, useRef, useState } from 'react';
import { AccessibilityInfo, Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Selo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { EscolhaSegmentada } from '@/components/EscolhaSegmentada';
import { EvitaTeclado } from '@/components/EvitaTeclado';
import { Hachura } from '@/components/Hachura';
import { Icone, type NomeIcone } from '@/components/Icone';
import { IlustracaoTextura } from '@/components/IlustracaoTextura';
import { EXEMPLOS_DE_COR, EXEMPLOS_DE_CORTE } from '@/data/catalogo';
import { useRascunho } from '@/data/rascunho';
import { useStore } from '@/data/store';
import type { Textura } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, fontes, raios } from '@/theme/tokens';
import {
  categoriaDaTextura,
  escolherCategoria,
  escolherTipo,
  MAX_DESCRICAO,
  OPCOES_DE_GENERO,
  OPCOES_DE_TEXTURA,
  pendencias,
  rotuloTextura,
  type CampoPedido,
  type Pendencia,
} from '@/utils/pedido';

type Secao = 'corte' | 'cor' | 'textura';
type Acao = 'mudar' | 'manter';

/** Cores claras sobre cabelo escuro saem menos fiéis: o aviso só aparece quando importa. */
const TOM_CLARO = /loir|platin|grisalh|prata|prate|branc|clar/i;

/**
 * Etapa 3 de 3: como o cabelo deve ficar na simulação.
 *
 * Três seções, na ordem em que um salão conversa: o corte, a cor e o tipo de cabelo. Cada
 * uma começa pela escolha entre mudar e manter, e só pede detalhes quando a pessoa quer
 * mudar. Corte e cor são descritos com as palavras de quem usa o aplicativo, sem lista
 * fechada; os exemplos ficam recolhidos, como inspiração. O tipo de cabelo é escolhido por
 * imagem: "Manter meu tipo de cabelo atual" já vem marcado, e cada tipo de 1A a 4C tem
 * uma ilustração própria.
 *
 * O botão "Revisar pedido" fica sempre ativo: com algo faltando, ele leva até a seção que
 * falta e mostra o que fazer, em vez de ficar apagado sem explicar o porquê. Texto escrito
 * antes de escolher "manter" não é descartado em silêncio: a seção pede uma decisão.
 */
export default function Parametros() {
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);
  const rolagem = useRef<ScrollView>(null);
  const posicoes = useRef<Record<Secao, number>>({ corte: 0, cor: 0, textura: 0 });
  const [mostrarErros, setMostrarErros] = useState(false);

  const faltas = pendencias({
    corte: rascunho.corte,
    manterCorte: rascunho.manterCorte,
    cor: rascunho.cor,
    manterCor: rascunho.manterCor,
    textura: rascunho.textura,
  });
  const faltaDe = (campo: CampoPedido) => faltas.find((f) => f.campo === campo);

  function irPara(pendencia: Pendencia) {
    const secao: Secao = pendencia.campo === 'cor' ? 'cor' : 'corte';
    rolagem.current?.scrollTo({ y: Math.max(0, posicoes.current[secao] - espaco.md), animated: true });
  }

  function revisar() {
    if (faltas.length > 0) {
      setMostrarErros(true);
      irPara(faltas[0]);
      AccessibilityInfo.announceForAccessibility?.(faltas[0].mensagem);
      return;
    }
    router.push('/simulacao/revisao');
  }

  // Guarda onde cada seção começa, para o rodapé levar até a que falta.
  function guardarPosicao(secao: Secao, y: number) {
    posicoes.current[secao] = y;
  }

  return (
    <Tela>
      <Cabecalho
        titulo="Estilo e cor"
        subtitulo={`Etapa 3 de 3${cliente ? ` · ${cliente.nome}` : ''}`}
        aoVoltar={() => router.back()}
        direita={
          rascunho.foto?.uri ? (
            <Image
              source={{ uri: rascunho.foto.uri }}
              style={styles.miniatura}
              accessibilityLabel="Foto do cliente que será usada"
            />
          ) : (
            <Hachura estilo={styles.miniatura} />
          )
        }
      />

      <EvitaTeclado>
        <ScrollView
          ref={rolagem}
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <Text style={textos.apoio}>
            Escolha o que muda no cabelo. Rosto, roupa e fundo continuam como estão na foto.
          </Text>

          <SecaoPedido
            rotulo="Corte"
            icone="corte"
            titulo="Como você quer que seu cabelo fique?"
            situacao={situacaoDoCampo(rascunho.manterCorte, faltaDe('corte'), mostrarErros)}
            aoMedir={(y) => guardarPosicao('corte', y)}>
            <EscolhaSegmentada<Acao>
              rotuloAcessivel="O que fazer com o corte"
              opcoes={[
                { valor: 'mudar', rotulo: 'Quero mudar' },
                { valor: 'manter', rotulo: 'Manter o corte atual' },
              ]}
              valor={rascunho.manterCorte ? 'manter' : 'mudar'}
              aoEscolher={(acao) => atualizar({ manterCorte: acao === 'manter' })}
            />
            {faltaDe('corte')?.tipo === 'conflito' ? (
              <Conflito
                texto={rascunho.corte}
                manter="Manter o corte atual"
                aoUsarTexto={() => atualizar({ manterCorte: false })}
                aoApagar={() => atualizar({ corte: '' })}
              />
            ) : rascunho.manterCorte ? (
              <Text style={textos.apoio}>O corte e o comprimento ficam como estão na foto.</Text>
            ) : (
              <>
                <View style={styles.bloco}>
                  <Text style={textos.etiqueta}>Estilo do corte</Text>
                  <EscolhaSegmentada
                    rotuloAcessivel="Estilo do corte: feminino, masculino ou neutro"
                    opcoes={OPCOES_DE_GENERO}
                    valor={rascunho.genero}
                    aoEscolher={(genero) => atualizar({ genero })}
                  />
                  <Text style={textos.meta}>Neutro é um corte sem gênero definido.</Text>
                </View>
                {/* A ajuda fica acima do campo, sempre à vista: o `Campo` troca a ajuda pelo erro. */}
                <Text style={textos.apoio}>
                  Descreva do seu jeito! Você pode informar o nome do corte, explicar os detalhes ou dizer
                  exatamente o que deseja mudar.
                </Text>
                <Campo
                  rotulo="Descrição do corte"
                  valor={rascunho.corte}
                  aoMudar={(corte) => atualizar({ corte })}
                  placeholder="Ex.: Quero manter o comprimento, adicionar camadas longas, uma franja cortininha e deixar as pontas mais leves..."
                  multilinha
                  limite={MAX_DESCRICAO}
                  erro={erroDoCampo(faltaDe('corte'), rascunho.corte, mostrarErros)}
                />
                <Inspiracoes assunto="cortes" grupos={EXEMPLOS_DE_CORTE} />
              </>
            )}
          </SecaoPedido>

          <SecaoPedido
            rotulo="Cor"
            icone="cor"
            titulo="Qual cor você deseja no seu cabelo?"
            situacao={situacaoDoCampo(rascunho.manterCor, faltaDe('cor'), mostrarErros)}
            aoMedir={(y) => guardarPosicao('cor', y)}>
            <EscolhaSegmentada<Acao>
              rotuloAcessivel="O que fazer com a cor"
              opcoes={[
                { valor: 'mudar', rotulo: 'Quero mudar' },
                { valor: 'manter', rotulo: 'Manter a cor atual' },
              ]}
              valor={rascunho.manterCor ? 'manter' : 'mudar'}
              aoEscolher={(acao) => atualizar({ manterCor: acao === 'manter' })}
            />
            {faltaDe('cor')?.tipo === 'conflito' ? (
              <Conflito
                texto={rascunho.cor}
                manter="Manter a cor atual"
                aoUsarTexto={() => atualizar({ manterCor: false })}
                aoApagar={() => atualizar({ cor: '' })}
              />
            ) : rascunho.manterCor ? (
              <Text style={textos.apoio}>A cor fica como está na foto, com as mechas e a raiz que já existem.</Text>
            ) : (
              <>
                <Text style={textos.apoio}>
                  Descreva a cor e todos os detalhes que imaginar. Você pode pedir mechas, luzes, reflexos,
                  degradês ou mudar apenas algumas partes do cabelo.
                </Text>
                <Campo
                  rotulo="Descrição da cor"
                  valor={rascunho.cor}
                  aoMudar={(cor) => atualizar({ cor })}
                  placeholder="Ex.: Quero manter a raiz castanho escuro, com mechas caramelo suaves no comprimento e pontas um pouco mais claras..."
                  multilinha
                  limite={MAX_DESCRICAO}
                  erro={erroDoCampo(faltaDe('cor'), rascunho.cor, mostrarErros)}
                />
                {TOM_CLARO.test(rascunho.cor) ? (
                  <Aviso
                    tom="neutro"
                    texto="Tons bem claros, como loiro claro, platinado e grisalho, sobre cabelo escuro tendem a sair menos fiéis na simulação."
                  />
                ) : null}
                <Inspiracoes assunto="cores" grupos={EXEMPLOS_DE_COR} />
              </>
            )}
          </SecaoPedido>

          <SecaoPedido
            rotulo="Tipo de cabelo"
            icone="textura"
            titulo="Qual tipo de cabelo você deseja na simulação?"
            ajuda="Escolha como o cabelo deve ficar na foto: mude a textura ou mantenha o tipo de cabelo atual."
            situacao={
              rascunho.textura
                ? { texto: 'Novo tipo', tom: 'sucesso', icone: 'okCirculo' }
                : { texto: 'Sem mudança', tom: 'neutro', icone: 'ok' }
            }
            aoMedir={(y) => guardarPosicao('textura', y)}>
            <EscolhaTextura
              valor={rascunho.textura}
              foto={rascunho.foto?.uri ?? null}
              aoEscolher={(textura) => atualizar({ textura })}
            />
          </SecaoPedido>
        </ScrollView>

        <View style={styles.rodape}>
          {faltas.length > 0 ? (
            <Pressable
              onPress={() => {
                setMostrarErros(true);
                irPara(faltas[0]);
              }}
              accessibilityRole="button"
              accessibilityLabel={`Falta completar. ${faltas[0].mensagem} Toque para ir até lá.`}
              style={({ pressed }) => [styles.rodapeLinha, pressed && styles.pressionado]}>
              <Icone nome="info" tamanho={14} cor={mostrarErros ? cores.erroTexto : cores.textoApoio} />
              <Text style={[textos.meta, styles.flex, mostrarErros && styles.faltaDestacada]} numberOfLines={2}>
                {faltas[0].mensagem}
                {faltas.length > 1 ? ` (e mais ${faltas.length - 1})` : ''}
              </Text>
              <Text style={textos.link}>Ver</Text>
            </Pressable>
          ) : (
            <View style={styles.rodapeLinha} accessibilityLiveRegion="polite">
              <Icone nome="okCirculo" tamanho={14} cor={cores.sucessoTexto} />
              <Text style={[textos.meta, styles.flex, styles.pronto]} numberOfLines={2}>
                Tudo pronto. Confira o resumo na próxima tela antes de gerar.
              </Text>
            </View>
          )}
          <Botao
            titulo="Revisar pedido"
            icone="avancar"
            dicaAcessivel={faltas.length > 0 ? `Falta completar: ${faltas[0].mensagem}` : undefined}
            aoPressionar={revisar}
          />
        </View>
      </EvitaTeclado>
    </Tela>
  );
}

type Situacao = { texto: string; tom: 'sucesso' | 'neutro' | 'erro' | 'alerta'; icone?: NomeIcone };

/** O selo de cada seção: o que já está pronto, o que falta e o que precisa de decisão. */
function situacaoDoCampo(manter: boolean, falta: Pendencia | undefined, mostrarErros: boolean): Situacao {
  if (falta?.tipo === 'conflito') return { texto: 'Decidir', tom: 'alerta', icone: 'alerta' };
  if (manter) return { texto: 'Sem mudança', tom: 'neutro', icone: 'ok' };
  if (falta?.tipo === 'texto') return { texto: 'Corrigir', tom: 'erro', icone: 'alerta' };
  if (falta?.tipo === 'vazio') {
    return mostrarErros ? { texto: 'Falta preencher', tom: 'erro', icone: 'alerta' } : { texto: 'A preencher', tom: 'neutro' };
  }
  return { texto: 'Pronto', tom: 'sucesso', icone: 'okCirculo' };
}

/**
 * O erro no próprio campo: texto inválido aparece na hora; campo vazio, só depois de a
 * pessoa tentar seguir (antes disso, é só um campo ainda não preenchido).
 */
function erroDoCampo(falta: Pendencia | undefined, texto: string, mostrarErros: boolean): string | null {
  if (!falta || falta.tipo === 'conflito' || falta.tipo === 'nada') return null;
  if (falta.tipo === 'vazio' && !mostrarErros) return null;
  if (falta.tipo === 'texto' && !texto.trim()) return null;
  const mensagem = falta.mensagem.replace(/^(Corte|Cor): /, '');
  return mensagem.charAt(0).toUpperCase() + mensagem.slice(1);
}

function SecaoPedido({
  rotulo,
  icone,
  titulo,
  ajuda,
  situacao,
  aoMedir,
  children,
}: {
  rotulo: string;
  icone: NomeIcone;
  titulo: string;
  ajuda?: string;
  situacao: Situacao;
  aoMedir: (y: number) => void;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.secao} onLayout={(evento) => aoMedir(evento.nativeEvent.layout.y)}>
      <View style={styles.secaoTopo}>
        <Icone nome={icone} tamanho={14} cor={cores.acaoTexto} />
        <Text style={[textos.etiqueta, styles.flex]}>{rotulo}</Text>
        <Selo texto={situacao.texto} tom={situacao.tom} icone={situacao.icone} />
      </View>
      <Text
        style={textos.secao}
        accessibilityRole="header"
        accessibilityLabel={`${rotulo}, ${situacao.texto.toLowerCase()}. ${titulo}`}>
        {titulo}
      </Text>
      {ajuda ? <Text style={textos.apoio}>{ajuda}</Text> : null}
      {children}
    </View>
  );
}

/** "Manter" escolhido com uma descrição já escrita: a pessoa decide qual vale. */
function Conflito({
  texto,
  manter,
  aoUsarTexto,
  aoApagar,
}: {
  texto: string;
  manter: string;
  aoUsarTexto: () => void;
  aoApagar: () => void;
}) {
  return (
    <Aviso
      tom="alerta"
      titulo="Você já escreveu uma descrição"
      texto={`Com "${manter}", ela não será aplicada na simulação. Qual deve valer?`}>
      <Text style={styles.citacao} numberOfLines={3}>
        “{texto.trim()}”
      </Text>
      <View style={styles.conflitoAcoes}>
        <Botao titulo="Usar a descrição" variante="secundaria" tamanho="pequeno" aoPressionar={aoUsarTexto} />
        <Botao titulo={`${manter} e apagar o texto`} variante="texto" tamanho="pequeno" aoPressionar={aoApagar} />
      </View>
    </Aviso>
  );
}

/** Exemplos recolhidos: inspiração para quem não sabe por onde começar, nunca uma lista fechada. */
function Inspiracoes({
  assunto,
  grupos,
}: {
  assunto: string;
  grupos: { emAlta: readonly string[]; classicos: readonly string[] };
}) {
  const [aberto, setAberto] = useState(false);
  const rotulo = aberto ? `Esconder ideias de ${assunto}` : `Sem ideias? Veja ${assunto} populares`;
  return (
    <View style={styles.inspiracoes}>
      <Pressable
        onPress={() => setAberto((valor) => !valor)}
        accessibilityRole="button"
        accessibilityLabel={rotulo}
        accessibilityState={{ expanded: aberto }}
        aria-expanded={aberto}
        style={({ pressed }) => [styles.inspiracoesTopo, pressed && styles.pressionado]}>
        <Icone nome="info" tamanho={14} cor={cores.acaoTexto} />
        <Text style={[textos.link, styles.flex]}>{rotulo}</Text>
        <View style={aberto ? styles.setaAberta : undefined}>
          <Icone nome="chevron" tamanho={14} cor={cores.acaoTexto} />
        </View>
      </Pressable>
      {aberto ? (
        <View style={styles.inspiracoesCorpo}>
          <Text style={textos.apoio}>
            <Text style={styles.grupo}>Em alta: </Text>
            {grupos.emAlta.join(', ')}.
          </Text>
          <Text style={textos.apoio}>
            <Text style={styles.grupo}>Clássicos: </Text>
            {grupos.classicos.join(', ')}.
          </Text>
          <Text style={textos.meta}>São só ideias: escreva do seu jeito, com os detalhes que quiser.</Text>
        </View>
      ) : null}
    </View>
  );
}

/**
 * Tipo de cabelo desejado: "Manter meu tipo de cabelo atual" (com a foto do cliente, para
 * ficar claro que é o cabelo dela) ou uma categoria, e dentro dela, se quiser, o tipo de
 * 1A a 4C. As categorias e os tipos são escolhas únicas: trocar de categoria troca o tipo,
 * e escolher "manter" desfaz os dois. A linha "Vai para a simulação" diz o valor final.
 */
function EscolhaTextura({
  valor,
  foto,
  aoEscolher,
}: {
  valor: Textura | null;
  foto: string | null;
  aoEscolher: (textura: Textura | null) => void;
}) {
  const [largura, setLargura] = useState(0);
  const categoria = categoriaDaTextura(valor);
  const opcao = OPCOES_DE_TEXTURA.find((o) => o.valor === categoria);
  // Quatro categorias numa linha só quando cada uma fica com pelo menos ~110 px. As
  // categorias têm desenho mais baixo que largo (cabem mais na tela); os tipos, quadrado
  // no celular (onde cada um é estreito) e baixo em tela larga, para não ficarem maiores
  // que as categorias.
  const larga = largura >= 470;
  const colunas = larga ? 4 : 2;

  return (
    <View style={styles.bloco} onLayout={(evento) => setLargura(evento.nativeEvent.layout.width)}>
      <View style={styles.bloco} accessibilityRole="radiogroup" accessibilityLabel="Tipo de cabelo desejado">
        <Pressable
          onPress={() => aoEscolher(null)}
          accessibilityRole="radio"
          accessibilityState={{ checked: valor === null }}
          aria-checked={valor === null}
          accessibilityLabel="Manter meu tipo de cabelo atual"
          style={({ pressed }) => [styles.manter, valor === null && styles.opcaoAtiva, pressed && styles.pressionado]}>
          {foto ? (
            <Image source={{ uri: foto }} style={styles.manterFoto} accessibilityIgnoresInvertColors />
          ) : (
            <View style={[styles.manterFoto, styles.manterSemFoto]}>
              <Icone nome="cliente" tamanho={20} cor={cores.textoApoio} />
            </View>
          )}
          <View style={styles.flex}>
            <Text style={[styles.opcaoTitulo, valor === null && styles.tituloAtivo]}>Manter meu tipo de cabelo atual</Text>
            <Text style={styles.opcaoDescricao}>
              A textura da foto é preservada: ondas, cachos e volume continuam os mesmos.
            </Text>
          </View>
          <Marca ativa={valor === null} />
        </Pressable>

        <Text style={textos.etiqueta}>Ou escolha um novo tipo</Text>
        <Grade colunas={colunas}>
          {OPCOES_DE_TEXTURA.map((o) => (
            <Ladrilho
              key={o.valor}
              textura={o.valor}
              proporcao={4 / 3}
              titulo={o.rotulo}
              descricao={o.descricao}
              ativo={categoria === o.valor}
              aoPressionar={() => aoEscolher(escolherCategoria(valor, o.valor))}
            />
          ))}
        </Grade>
      </View>

      {opcao ? (
        <View style={styles.subtipos}>
          <Text style={textos.corpoForte}>Qual {opcao.rotulo.toLowerCase()} você deseja?</Text>
          <Text style={textos.meta}>
            Opcional. Escolha o mais parecido com o que imagina; toque de novo para desmarcar.
          </Text>
          <View accessibilityRole="radiogroup" accessibilityLabel={`Tipo de ${opcao.rotulo.toLowerCase()}`}>
            <Grade colunas={3}>
              {opcao.tipos.map((tipo) => (
                <Ladrilho
                  key={tipo.valor}
                  textura={tipo.valor}
                  proporcao={larga ? 3 / 2 : 1}
                  titulo={tipo.valor}
                  descricao={tipo.descricao}
                  ativo={valor === tipo.valor}
                  aoPressionar={() => aoEscolher(escolherTipo(valor, tipo.valor))}
                />
              ))}
            </Grade>
          </View>
        </View>
      ) : null}

      <View style={styles.escolhido} accessibilityLiveRegion="polite">
        <Text style={textos.meta}>Vai para a simulação:</Text>
        <Text style={[textos.apoioForte, styles.flex]}>
          {valor === null ? 'manter o tipo de cabelo atual' : rotuloTextura(valor)}
        </Text>
      </View>
    </View>
  );
}

/** Grade de colunas iguais que quebra em linhas; a última linha é completada com vazios. */
function Grade({ colunas, children }: { colunas: number; children: React.ReactNode }) {
  const itens = Children.toArray(children);
  const linhas: React.ReactNode[][] = [];
  for (let i = 0; i < itens.length; i += colunas) linhas.push(itens.slice(i, i + colunas));
  return (
    <View style={styles.grade}>
      {linhas.map((linha, i) => (
        <View key={i} style={styles.gradeLinha}>
          {linha.map((item, j) => (
            <View key={j} style={styles.gradeCelula}>
              {item}
            </View>
          ))}
          {Array.from({ length: colunas - linha.length }, (_, k) => (
            <View key={`vazio-${k}`} style={styles.gradeCelula} />
          ))}
        </View>
      ))}
    </View>
  );
}

function Ladrilho({
  textura,
  proporcao,
  titulo,
  descricao,
  ativo,
  aoPressionar,
}: {
  textura: Textura;
  proporcao: number;
  titulo: string;
  descricao: string;
  ativo: boolean;
  aoPressionar: () => void;
}) {
  return (
    <Pressable
      onPress={aoPressionar}
      accessibilityRole="radio"
      accessibilityState={{ checked: ativo }}
      aria-checked={ativo}
      accessibilityLabel={`${titulo}: ${descricao}`}
      style={({ pressed }) => [styles.ladrilho, ativo && styles.opcaoAtiva, pressed && styles.pressionado]}>
      <IlustracaoTextura textura={textura} proporcao={proporcao} />
      <View style={styles.ladrilhoTexto}>
        <Text style={[styles.opcaoTitulo, ativo && styles.tituloAtivo]}>{titulo}</Text>
        <Text style={styles.opcaoDescricao}>{descricao}</Text>
      </View>
      <View style={styles.ladrilhoMarca}>
        <Marca ativa={ativo} />
      </View>
    </Pressable>
  );
}

/** O círculo de seleção: vazio ou preenchido com o visto. */
function Marca({ ativa }: { ativa: boolean }) {
  return (
    <View style={[styles.marca, ativa && styles.marcaAtiva]}>
      {ativa ? <Icone nome="ok" tamanho={12} cor="#FFFFFF" /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, minWidth: 0 },
  miniatura: { width: 44, height: 56, borderRadius: raios.campo },
  conteudo: { paddingHorizontal: espaco.lg, paddingTop: espaco.lg, paddingBottom: espaco.xxl, gap: espaco.lg },
  secao: {
    gap: espaco.md,
    padding: espaco.lg,
    borderRadius: raios.cartao,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.superficie,
  },
  secaoTopo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  bloco: { gap: espaco.sm },
  pressionado: { opacity: 0.85 },
  citacao: {
    fontFamily: fontes.sans,
    fontSize: 13,
    lineHeight: 19,
    color: cores.alertaTexto,
    fontStyle: 'italic',
  },
  conflitoAcoes: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: espaco.sm, marginTop: espaco.xs },
  inspiracoes: { borderRadius: raios.campo, backgroundColor: cores.superficieSuave },
  inspiracoesTopo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.sm,
    minHeight: ALVO_TOQUE,
    paddingHorizontal: espaco.md,
  },
  setaAberta: { transform: [{ rotate: '90deg' }] },
  inspiracoesCorpo: { gap: espaco.xs, paddingHorizontal: espaco.md, paddingBottom: espaco.md },
  grupo: { fontFamily: fontes.sansSemi, color: cores.texto },
  manter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    padding: espaco.md,
    minHeight: ALVO_TOQUE,
    borderRadius: raios.campo,
    borderWidth: 2,
    borderColor: cores.borda,
    backgroundColor: cores.superficie,
  },
  manterFoto: { width: 48, height: 60, borderRadius: raios.campo - 2, backgroundColor: cores.superficieSuave },
  manterSemFoto: { alignItems: 'center', justifyContent: 'center' },
  opcaoAtiva: { borderColor: cores.acao, backgroundColor: cores.acaoSuave },
  opcaoTitulo: { fontFamily: fontes.sansSemi, fontSize: 14, lineHeight: 18, color: cores.texto },
  tituloAtivo: { color: cores.acaoTexto },
  opcaoDescricao: { fontFamily: fontes.sans, fontSize: 12, lineHeight: 16, color: cores.textoApoio },
  grade: { gap: espaco.sm },
  gradeLinha: { flexDirection: 'row', gap: espaco.sm },
  gradeCelula: { flex: 1, minWidth: 0 },
  ladrilho: {
    flexGrow: 1,
    gap: espaco.sm,
    padding: espaco.sm,
    borderRadius: raios.campo,
    borderWidth: 2,
    borderColor: cores.borda,
    backgroundColor: cores.superficie,
  },
  ladrilhoTexto: { gap: 2 },
  ladrilhoMarca: { position: 'absolute', top: espaco.xs, right: espaco.xs },
  marca: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: cores.bordaForte,
    backgroundColor: cores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
  },
  marcaAtiva: { borderColor: cores.acao, backgroundColor: cores.acao },
  subtipos: {
    gap: espaco.sm,
    padding: espaco.md,
    borderRadius: raios.campo,
    backgroundColor: cores.superficieSuave,
  },
  escolhido: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline', columnGap: espaco.xs },
  rodape: {
    paddingHorizontal: espaco.lg,
    paddingTop: espaco.xs,
    paddingBottom: espaco.md,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
    gap: espaco.xs,
  },
  rodapeLinha: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm, minHeight: ALVO_TOQUE },
  faltaDestacada: { color: cores.erroTexto },
  pronto: { color: cores.sucessoTexto },
});
