import { useRouter } from 'expo-router';
import {
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { Aviso, Chip, Selo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { Hachura } from '@/components/Hachura';
import { Icone, type NomeIcone } from '@/components/Icone';
import { EXEMPLOS_DE_COR, EXEMPLOS_DE_CORTE } from '@/data/catalogo';
import { useRascunho } from '@/data/rascunho';
import { useStore } from '@/data/store';
import type { Genero } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, fontes, raios } from '@/theme/tokens';
import { MAX_DESCRICAO, OPCOES_DE_GENERO, pendencias, type CampoPedido } from '@/utils/pedido';

const COMO_PREENCHER = [
  'Corte: escolha o gênero e escreva o novo corte, ou marque "Manter o corte atual".',
  'Cor: escreva a nova cor ou marque "Manter a cor atual".',
  'Toque em "Revisar pedido" para conferir. A imagem só é gerada depois da revisão.',
];

/**
 * Etapa 3 de 3: o que mudar no cabelo.
 *
 * A tela é um roteiro de dois passos, corte e depois cor. Cada passo diz o que escrever,
 * mostra exemplos e permite manter o que já existe; o selo ao lado do título mostra se o
 * passo está pronto. O passo do corte também pergunta o gênero do corte, que vai ao modelo
 * de simulação; "Não especificar" já vem marcado e é o padrão do próprio modelo. Os
 * exemplos são só texto: o pedido é escrito com as palavras do profissional. Nada aqui gera
 * imagem: o próximo passo é revisar o pedido.
 */
export default function Parametros() {
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);

  const faltas = pendencias({
    corte: rascunho.corte,
    manterCorte: rascunho.manterCorte,
    cor: rascunho.cor,
    manterCor: rascunho.manterCor,
  });
  // Campo vazio não é erro enquanto a pessoa não escreveu nada: aparece só no selo e no
  // rodapé. Texto inválido (longo, com marcação) aparece no próprio campo, na hora.
  const problema = (campo: CampoPedido, texto: string) =>
    texto.trim() ? (faltas.find((f) => f.campo === campo)?.mensagem ?? null) : null;
  const problemaCorte = problema('corte', rascunho.corte);
  const problemaCor = problema('cor', rascunho.cor);

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

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
        keyboardVerticalOffset={20}>
        <ScrollView
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <View style={styles.guia}>
            <Text style={textos.corpoForte} accessibilityRole="header">
              Como preencher
            </Text>
            <Text style={textos.apoio}>
              Escreva com suas palavras o que o cliente quer. A simulação muda só o cabelo. Rosto,
              roupa e fundo continuam os da foto.
            </Text>
            {COMO_PREENCHER.map((passo, indice) => (
              <View key={passo} style={styles.guiaLinha}>
                <Text style={styles.guiaNumero}>{indice + 1}.</Text>
                <Text style={[textos.apoio, styles.flex]}>{passo}</Text>
              </View>
            ))}
          </View>

          <Passo
            numero={1}
            titulo="Corte"
            situacao={situacaoDoPasso(rascunho.manterCorte, rascunho.corte, problemaCorte)}>
            <EscolhaGenero valor={rascunho.genero} aoEscolher={(genero) => atualizar({ genero })} />
            <Text style={textos.apoio}>
              {rascunho.manterCorte
                ? 'O corte fica como está na foto. Desmarque para descrever um corte novo.'
                : 'Escreva o corte que o cliente quer ver na simulação.'}
            </Text>
            <CaixaMarcar
              rotulo="Manter o corte atual (mudar só a cor)"
              marcado={rascunho.manterCorte}
              aoAlternar={(manterCorte) => atualizar({ manterCorte })}
            />
            {!rascunho.manterCorte ? (
              <>
                <Campo
                  rotulo="Novo corte"
                  valor={rascunho.corte}
                  aoMudar={(corte) => atualizar({ corte })}
                  placeholder="Ex.: chanel na altura do queixo, com franja leve"
                  multilinha
                  limite={MAX_DESCRICAO}
                  erro={problemaCorte}
                  ajuda="Pode ser só o nome do corte, ou o nome com detalhes de comprimento, franja e camadas."
                />
                <Exemplos titulo="Exemplos de corte que você pode escrever" grupos={EXEMPLOS_DE_CORTE} />
              </>
            ) : null}
          </Passo>

          <Passo
            numero={2}
            titulo="Cor"
            situacao={situacaoDoPasso(rascunho.manterCor, rascunho.cor, problemaCor)}>
            <Text style={textos.apoio}>
              {rascunho.manterCor
                ? 'A cor fica como está na foto. Desmarque para descrever uma cor nova.'
                : 'Escreva a cor que o cliente quer ver na simulação.'}
            </Text>
            <CaixaMarcar
              rotulo="Manter a cor atual (mudar só o corte)"
              marcado={rascunho.manterCor}
              aoAlternar={(manterCor) => atualizar({ manterCor })}
            />
            {!rascunho.manterCor ? (
              <>
                <Campo
                  rotulo="Nova cor"
                  valor={rascunho.cor}
                  aoMudar={(cor) => atualizar({ cor })}
                  placeholder="Ex.: castanho chocolate com reflexos caramelo"
                  multilinha
                  limite={MAX_DESCRICAO}
                  erro={problemaCor}
                  ajuda="Pode ser só o nome da cor, ou o nome com detalhes de tom, reflexos e mechas."
                />
                <Exemplos titulo="Exemplos de cor que você pode escrever" grupos={EXEMPLOS_DE_COR} />
                <Aviso
                  tom="neutro"
                  texto="Tons bem claros, como loiro claro, platinado e grisalho, sobre cabelo escuro tendem a sair menos fiéis na simulação."
                />
              </>
            ) : null}
          </Passo>
        </ScrollView>

        <View style={styles.rodape}>
          <View style={styles.rodapeLinha} accessibilityLiveRegion="polite">
            <Icone
              nome={faltas.length > 0 ? 'info' : 'okCirculo'}
              tamanho={14}
              cor={faltas.length > 0 ? cores.textoApoio : cores.sucessoTexto}
            />
            <Text style={[textos.meta, styles.flex, faltas.length === 0 && styles.pronto]}>
              {faltas.length > 0 ? faltas[0].mensagem : 'Pedido completo. Confira tudo na próxima tela antes de gerar.'}
            </Text>
          </View>
          <Botao
            titulo="Revisar pedido"
            icone="avancar"
            desabilitado={faltas.length > 0}
            dicaAcessivel={faltas.length > 0 ? faltas[0].mensagem : undefined}
            aoPressionar={() => router.push('/simulacao/revisao')}
          />
        </View>
      </KeyboardAvoidingView>
    </Tela>
  );
}

type Situacao = { texto: string; tom: 'sucesso' | 'neutro' | 'erro'; icone?: NomeIcone };

/** O selo de cada passo: o profissional vê de relance o que já está pronto. */
function situacaoDoPasso(manter: boolean, texto: string, problema: string | null): Situacao {
  if (manter) return { texto: 'Sem mudança', tom: 'neutro', icone: 'ok' };
  if (!texto.trim()) return { texto: 'A preencher', tom: 'neutro' };
  if (problema) return { texto: 'Corrigir', tom: 'erro', icone: 'alerta' };
  return { texto: 'Pronto', tom: 'sucesso', icone: 'okCirculo' };
}

function Passo({
  numero,
  titulo,
  situacao,
  children,
}: {
  numero: number;
  titulo: string;
  situacao: Situacao;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.passo}>
      <View style={styles.passoTopo}>
        <View style={styles.numero} aria-hidden importantForAccessibility="no-hide-descendants">
          <Text style={styles.numeroTexto}>{numero}</Text>
        </View>
        <Text
          style={[textos.secao, styles.flex]}
          accessibilityRole="header"
          accessibilityLabel={`Passo ${numero}: ${titulo}, ${situacao.texto.toLowerCase()}`}>
          {titulo}
        </Text>
        <Selo texto={situacao.texto} tom={situacao.tom} icone={situacao.icone} />
      </View>
      {children}
    </View>
  );
}

function CaixaMarcar({
  rotulo,
  marcado,
  aoAlternar,
}: {
  rotulo: string;
  marcado: boolean;
  aoAlternar: (marcado: boolean) => void;
}) {
  return (
    <Pressable
      onPress={() => aoAlternar(!marcado)}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: marcado }}
      // O `accessibilityState` não chega ao HTML na web; o atributo ARIA chega.
      aria-checked={marcado}
      accessibilityLabel={rotulo}
      style={({ pressed }) => [styles.caixaLinha, pressed && styles.pressionado]}>
      <View style={[styles.caixa, marcado && styles.caixaMarcada]}>
        {marcado ? <Icone nome="ok" tamanho={14} cor="#FFFFFF" /> : null}
      </View>
      <Text style={styles.caixaTexto}>{rotulo}</Text>
    </Pressable>
  );
}

/** Gênero do corte, escolha única. Vale também quando o corte é mantido e só a cor muda. */
function EscolhaGenero({ valor, aoEscolher }: { valor: Genero; aoEscolher: (genero: Genero) => void }) {
  return (
    <View style={styles.genero}>
      <Text style={textos.etiqueta}>Gênero</Text>
      <View style={styles.chips} accessibilityRole="radiogroup" accessibilityLabel="Gênero do corte">
        {OPCOES_DE_GENERO.map((opcao) => (
          <Chip
            key={opcao.valor}
            texto={opcao.rotulo}
            ativo={valor === opcao.valor}
            aoPressionar={() => aoEscolher(opcao.valor)}
          />
        ))}
      </View>
      <Text style={textos.apoio}>O corte desejado é feminino ou masculino? A escolha orienta a simulação.</Text>
    </View>
  );
}

/** Exemplos em texto corrido: mostram o que dá para pedir, sem virar botão. */
function Exemplos({
  titulo,
  grupos,
}: {
  titulo: string;
  grupos: { emAlta: readonly string[]; classicos: readonly string[] };
}) {
  return (
    <View style={styles.exemplos}>
      <Text style={textos.etiqueta}>{titulo}</Text>
      <Text style={textos.apoio}>
        <Text style={styles.grupo}>Em alta: </Text>
        {grupos.emAlta.join(', ')}.
      </Text>
      <Text style={textos.apoio}>
        <Text style={styles.grupo}>Clássicos: </Text>
        {grupos.classicos.join(', ')}.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  miniatura: { width: 44, height: 56, borderRadius: raios.campo },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxl, gap: espaco.lg },
  guia: {
    gap: espaco.sm,
    padding: espaco.lg,
    borderRadius: raios.cartao,
    backgroundColor: cores.superficieSuave,
  },
  guiaLinha: { flexDirection: 'row', gap: espaco.sm },
  guiaNumero: { fontFamily: fontes.sansSemi, fontSize: 13, lineHeight: 19, color: cores.acaoTexto, minWidth: 16 },
  passo: {
    gap: espaco.md,
    padding: espaco.lg,
    borderRadius: raios.cartao,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.superficie,
  },
  passoTopo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  numero: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: cores.acao,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numeroTexto: { fontFamily: fontes.sansSemi, fontSize: 14, color: '#FFFFFF' },
  caixaLinha: { flexDirection: 'row', alignItems: 'center', gap: espaco.md, minHeight: ALVO_TOQUE },
  caixa: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: cores.bordaForte,
    backgroundColor: cores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
  },
  caixaMarcada: { backgroundColor: cores.acao, borderColor: cores.acao },
  caixaTexto: { fontFamily: fontes.sansMedio, fontSize: 15, color: cores.texto, flexShrink: 1 },
  pressionado: { opacity: 0.85 },
  genero: { gap: espaco.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.sm },
  exemplos: {
    gap: espaco.xs,
    padding: espaco.md,
    borderRadius: raios.campo,
    backgroundColor: cores.superficieSuave,
  },
  grupo: { fontFamily: fontes.sansSemi, color: cores.texto },
  rodape: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
    gap: espaco.sm,
  },
  rodapeLinha: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: espaco.sm },
  pronto: { color: cores.sucessoTexto },
});
