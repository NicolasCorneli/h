import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { Icone } from '@/components/Icone';
import { useRascunho } from '@/data/rascunho';
import { RESUMO_ENVIO } from '@/data/servicoExterno';
import { useStore } from '@/data/store';
import type { PlanoSimulacao } from '@/data/tipos';
import { ErroApi, simulacoes } from '@/services/api';
import { useModoDemo } from '@/services/modoDemo';
import { textos } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, fontes, raios } from '@/theme/tokens';
import { pendencias, rotuloCor, rotuloCorte, rotuloGenero, type EscolhasPedido } from '@/utils/pedido';

/**
 * Revisão do pedido, antes de gastar uma geração.
 *
 * Mostra a foto que vai ser usada, o corte e a cor, cada um com como editar ou deixar como
 * está. Pergunta ao servidor como o pedido será gerado (modo, modelo e o que vai para ele,
 * sem foto e sem custo). Só daqui sai o "Gerar simulação".
 */
export default function Revisao() {
  const router = useRouter();
  const modoDemo = useModoDemo();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);
  const [plano, setPlano] = useState<PlanoSimulacao | null>(null);
  const [erroPlano, setErroPlano] = useState<ErroApi | null>(null);
  const [verInstrucao, setVerInstrucao] = useState(false);
  const enviando = useRef(false);

  const escolhas: EscolhasPedido = {
    corte: rascunho.corte,
    manterCorte: rascunho.manterCorte,
    cor: rascunho.cor,
    manterCor: rascunho.manterCor,
  };
  const faltas = pendencias(escolhas);
  // O gênero muda o que vai ao modelo: entra na prévia e, quando muda, ela é refeita.
  const pedido = { ...escolhas, genero: rascunho.genero };
  const chavePlano = JSON.stringify(pedido);

  // Sem foto (recarregou a página, por exemplo), não há o que revisar. Confere só ao abrir:
  // esta tela continua montada na pilha depois do resultado, e o rascunho é limpo ao
  // registrar o atendimento. Reagir a essa limpeza tirava o profissional da tela de
  // sucesso e o mandava para a câmera.
  useEffect(() => {
    if (!rascunho.foto || !rascunho.clienteId) router.replace('/simulacao/captura');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (faltas.length > 0) {
      setPlano(null);
      return;
    }
    let ativo = true;
    setErroPlano(null);
    simulacoes
      .plano(pedido)
      .then((resposta) => ativo && setPlano(resposta))
      .catch((falha) => {
        if (!ativo) return;
        setPlano(null);
        setErroPlano(falha instanceof ErroApi ? falha : new ErroApi('Falha ao consultar', 'desconhecido', 0));
      });
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chavePlano]);

  // Recusa do servidor (pedido inválido, recurso desligado) impede gerar. Falta de
  // conexão na prévia, não: a prévia é informativa, e a geração diz o que houver.
  const recusado = !!erroPlano && !erroPlano.deConexao && erroPlano.status === 422;
  const podeGerar = faltas.length === 0 && !recusado;
  // "Não mudar" só aparece quando corte e cor mudam: manter os dois não é pedido.
  const mudaOsDois = !rascunho.manterCorte && !rascunho.manterCor;

  function gerar(demoFalharIa = false) {
    if (!podeGerar || enviando.current) return;
    enviando.current = true;
    atualizar({ demoFalharIa });
    router.push('/simulacao/processando');
    // A tela de processamento assume daqui; ao voltar para cá, o botão vale de novo.
    setTimeout(() => {
      enviando.current = false;
    }, 1500);
  }

  return (
    <Tela>
      <Cabecalho
        titulo="Revisar pedido"
        subtitulo={`Etapa 3 de 3${cliente ? ` · ${cliente.nome}` : ''}`}
        aoVoltar={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        <View style={styles.colunaFoto}>
          <Text style={[textos.etiqueta, styles.rotuloFoto]}>Foto do cliente</Text>
          {rascunho.foto ? (
            <Image
              source={{ uri: rascunho.foto.uri }}
              style={styles.foto}
              accessibilityLabel="Foto do cliente que será enviada"
            />
          ) : null}
        </View>

        <View style={styles.cartao}>
          <LinhaPedido
            rotulo="Corte"
            valor={rotuloCorte(escolhas)}
            acoes={[
              { titulo: 'Editar', aoPressionar: () => router.back() },
              ...(mudaOsDois
                ? [{ titulo: 'Não mudar', aoPressionar: () => atualizar({ manterCorte: true, corte: '' }) }]
                : []),
            ]}
          />
          <LinhaPedido
            rotulo="Gênero"
            valor={rotuloGenero(rascunho.genero)}
            acoes={[{ titulo: 'Editar', aoPressionar: () => router.back() }]}
          />
          <LinhaPedido
            rotulo="Cor"
            valor={rotuloCor(escolhas)}
            acoes={[
              { titulo: 'Editar', aoPressionar: () => router.back() },
              ...(mudaOsDois
                ? [{ titulo: 'Não mudar', aoPressionar: () => atualizar({ manterCor: true, cor: '' }) }]
                : []),
            ]}
            ultima
          />
        </View>

        {faltas.length > 0 ? (
          <Aviso tom="alerta" titulo="Falta completar o pedido" texto={faltas.map((f) => f.mensagem).join(' ')} />
        ) : null}

        {recusado && erroPlano ? <Aviso tom="erro" texto={erroPlano.message} /> : null}

        {plano ? (
          <View style={styles.cartao}>
            <Text style={textos.etiqueta}>Como será gerado</Text>
            <Text style={textos.corpoForte}>{plano.descricaoModo}</Text>
            <Text style={textos.meta}>Modelo: {plano.modelo}</Text>
            {plano.provedor === 'fake' ? (
              <Text style={textos.meta}>
                O servidor está no modo local, sem serviço de IA: a imagem sai com aviso e o corte não muda.
              </Text>
            ) : null}
            <Pressable
              onPress={() => setVerInstrucao((v) => !v)}
              accessibilityRole="button"
              accessibilityState={{ expanded: verInstrucao }}
              accessibilityLabel={verInstrucao ? 'Esconder o que vai para o modelo' : 'Ver o que vai para o modelo'}
              style={styles.alternar}>
              <Text style={textos.link}>{verInstrucao ? 'Esconder o que vai para o modelo' : 'Ver o que vai para o modelo'}</Text>
              <Icone nome="chevron" tamanho={14} cor={cores.acaoTexto} />
            </Pressable>
            {verInstrucao ? (
              <Text style={styles.instrucao} selectable>
                {plano.instrucao}
              </Text>
            ) : null}
          </View>
        ) : null}

        <Aviso tom="neutro" titulo="O que é enviado" texto={RESUMO_ENVIO} />

        <Campo
          rotulo="Anotação para o histórico"
          valor={rascunho.observacoes}
          aoMudar={(observacoes) => atualizar({ observacoes })}
          placeholder="O que o cliente pediu, o que evitar…"
          multilinha
          marcaOpcional
          ajuda="Fica só no aplicativo. Não vai para o serviço de IA."
          estilo={styles.anotacao}
        />
      </ScrollView>

      <View style={styles.rodape}>
        <Botao
          titulo="Gerar simulação"
          variante="acao"
          icone="simulacao"
          desabilitado={!podeGerar}
          dicaAcessivel={!podeGerar ? 'Complete o pedido antes de gerar' : undefined}
          aoPressionar={() => gerar(false)}
        />
        <Text style={[textos.meta, styles.tempo]}>
          Costuma levar de 10 a 40 segundos. Cada geração usa crédito do serviço de IA.
        </Text>
        {/*
          Demonstração do caminho de erro: a marca vai ao servidor, que responde como se o
          provedor estivesse fora do ar. Só tem efeito com o servidor em modo demo.
        */}
        {modoDemo && podeGerar ? (
          <Botao
            titulo="Ver o que acontece se a simulação falhar"
            variante="texto"
            tamanho="pequeno"
            aoPressionar={() => gerar(true)}
          />
        ) : null}
      </View>
    </Tela>
  );
}

type Acao = { titulo: string; aoPressionar: () => void };

function LinhaPedido({
  rotulo,
  valor,
  acoes,
  ultima = false,
}: {
  rotulo: string;
  valor: string;
  acoes: Acao[];
  ultima?: boolean;
}) {
  return (
    <View style={[styles.linha, !ultima && styles.linhaDivisoria]}>
      <Text style={textos.etiqueta}>{rotulo}</Text>
      <Text style={textos.corpoForte}>{valor}</Text>
      <View style={styles.acoes}>
        {acoes.map((acao) => (
          <Pressable
            key={acao.titulo}
            onPress={acao.aoPressionar}
            accessibilityRole="button"
            accessibilityLabel={`${acao.titulo}: ${rotulo.toLowerCase()}`}
            style={styles.acao}>
            <Text style={textos.link}>{acao.titulo}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxl, gap: espaco.lg },
  colunaFoto: { width: '100%', maxWidth: 170 },
  rotuloFoto: { marginBottom: espaco.sm },
  foto: { width: '100%', aspectRatio: 3 / 4, borderRadius: raios.cartao, backgroundColor: cores.superficieSuave },
  cartao: {
    backgroundColor: cores.superficie,
    borderRadius: raios.cartao,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espaco.lg,
    gap: espaco.xs,
  },
  linha: { gap: espaco.xs, paddingVertical: espaco.sm },
  linhaDivisoria: { borderBottomWidth: 1, borderBottomColor: cores.bordaSuave },
  acoes: { flexDirection: 'row', flexWrap: 'wrap', columnGap: espaco.lg },
  acao: { minHeight: ALVO_TOQUE, justifyContent: 'center' },
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
  anotacao: { marginTop: espaco.xs },
  rodape: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
  },
  tempo: { textAlign: 'center', marginTop: espaco.sm },
});
