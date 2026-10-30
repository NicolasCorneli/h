import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Avatar, BotaoIcone, Cartao, Selo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { useFeedback } from '@/components/Feedback';
import { ItemHistorico } from '@/components/ItemHistorico';
import { Icone } from '@/components/Icone';
import { ImagemSimulada } from '@/components/ImagemSimulada';
import { SeloConsentimento } from '@/components/SeloConsentimento';
import {
  useCliente,
  useHistoricoConsentimento,
  useHistoricoDoCliente,
  useResumoConsentimento,
  useSimulacoesDoCliente,
  useStore,
} from '@/data/store';
import type { ResumoConsentimento, Simulacao } from '@/data/tipos';
import { ErroApi } from '@/services/api';
import { exigeResponsavel, idadeEm, rotuloFormaObtencao } from '@/services/consentService';
import { textos, textosEscuros } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, fontes, raios } from '@/theme/tokens';
import { dataCurta, diaMes } from '@/utils/datas';

const DECISAO = { aceito: 'Aceitou', recusado: 'Recusou', revogado: 'Cancelou' } as const;

function textoDoConsentimento(resumo: ResumoConsentimento, nome: string): string {
  const primeiro = nome.split(' ')[0];
  if (!resumo.registro) {
    return `${primeiro} ainda não decidiu sobre o uso da própria imagem. Apresente o termo no próximo atendimento.`;
  }
  const quando = dataCurta(resumo.registro.registradoEm);
  if (resumo.revalidar) {
    return `Aceitou em ${quando}, sobre a versão ${resumo.registro.versaoTermo} do termo. A versão atual é a ${resumo.versaoVigente} e precisa ser apresentada antes da próxima foto.`;
  }
  if (resumo.status === 'aceito') return `Autorizou o uso da imagem em ${quando}.`;
  if (resumo.status === 'recusado') {
    return `Recusou o uso da imagem em ${quando}. Cadastro, histórico e agenda seguem normais.`;
  }
  return `Cancelou o consentimento em ${quando}.`;
}

/** T4 — centro de gravidade do app: identidade, consentimento, simulações e histórico. */
export default function PerfilCliente() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { acoes } = useStore();
  const { avisar, confirmar } = useFeedback();
  const cliente = useCliente(id);
  const simulacoes = useSimulacoesDoCliente(id);
  const historico = useHistoricoDoCliente(id);
  const resumo = useResumoConsentimento(id);
  const decisoes = useHistoricoConsentimento(id);
  const [verDecisoes, setVerDecisoes] = useState(false);
  // A simulação sendo excluída ou marcada: um segundo toque não manda outro pedido.
  const [excluindo, setExcluindo] = useState<string | null>(null);
  const [preferindo, setPreferindo] = useState<string | null>(null);

  const menor = exigeResponsavel(cliente);
  const idade = idadeEm(cliente?.dataNascimento ?? null);

  if (!cliente) {
    return (
      <Tela>
        <View style={styles.ausente}>
          <Text style={textos.secao}>Cliente não encontrado</Text>
          <Botao
            titulo="Voltar para a lista"
            variante="texto"
            aoPressionar={() => router.replace('/(tabs)/clientes')}
          />
        </View>
      </Tela>
    );
  }

  async function revogar() {
    if (!cliente) return;
    const confirmado = await confirmar({
      titulo: 'Cancelar o consentimento?',
      mensagem: `${cliente.nome} deixa de autorizar o uso da imagem. Novas simulações ficam bloqueadas; cadastro, histórico e agenda continuam normais.`,
      rotuloConfirmar: 'Cancelar consentimento',
      rotuloCancelar: 'Voltar',
      destrutivo: true,
    });
    if (!confirmado) return;

    try {
      // Revogar é inserir um registro novo: o histórico anterior permanece (art. 37).
      // A versão do termo é definida pelo servidor, a partir do aceite que está sendo
      // cancelado.
      await acoes.registrarConsentimento(cliente.id, {
        decisao: 'revogado',
        formaObtencao: 'lido_em_voz_alta',
        // O responsável só vai junto se o cliente ainda é menor. Quem aceitou com 17 anos
        // e já fez 18 revoga por si: mandar o responsável antigo fazia o servidor recusar
        // a revogação ("responsável só se aplica a menor"), e a pessoa não conseguia
        // retirar o consentimento.
        confirmadoPor: (menor ? resumo.registro?.responsavel?.nome : null) ?? cliente.nome,
        responsavel: menor ? (resumo.registro?.responsavel ?? null) : null,
        observacao: 'Cancelamento solicitado pelo cliente.',
      });
      avisar('Consentimento cancelado');
    } catch (falha) {
      avisar(
        falha instanceof ErroApi ? falha.message : 'Não foi possível cancelar agora',
        'erro'
      );
      return;
    }

    if (simulacoes.length === 0) return;
    const apagar = await confirmar({
      titulo: 'Apagar as simulações salvas?',
      mensagem: `${cliente.nome} tem ${simulacoes.length} ${
        simulacoes.length === 1 ? 'simulação salva' : 'simulações salvas'
      }. O cancelamento dá direito à eliminação dessas imagens (LGPD, art. 18, VI). O histórico de atendimentos é preservado.`,
      rotuloConfirmar: 'Apagar imagens',
      rotuloCancelar: 'Manter',
      destrutivo: true,
    });
    if (apagar) {
      try {
        await acoes.excluirImagensDoCliente(cliente.id);
        avisar('Imagens apagadas');
      } catch (falha) {
        avisar(
          falha instanceof ErroApi ? falha.message : 'Não foi possível apagar as imagens',
          'erro'
        );
      }
    }
  }

  async function marcarPreferida(simulacao: Simulacao) {
    if (!cliente || simulacao.preferida || preferindo) return;
    setPreferindo(simulacao.id);
    try {
      // Só uma preferida por cliente, garantido por índice único no banco: a anterior
      // deixa de ser.
      await acoes.marcarPreferida(cliente.id, simulacao.id);
      avisar(`${simulacao.parametros.cor} marcada como preferida`);
    } catch (falha) {
      avisar(
        falha instanceof ErroApi ? falha.message : 'Não foi possível marcar a preferida',
        'erro'
      );
    } finally {
      setPreferindo(null);
    }
  }

  async function excluirSimulacao(simulacao: Simulacao) {
    if (!cliente || excluindo) return;
    const confirmado = await confirmar({
      titulo: 'Excluir esta simulação?',
      mensagem: `A simulação de ${diaMes(simulacao.criadoEm)} (${simulacao.parametros.estilo} · ${simulacao.parametros.cor}) é apagada, junto com a foto enviada e a imagem gerada. O histórico de atendimentos é preservado.`,
      rotuloConfirmar: 'Excluir simulação',
      rotuloCancelar: 'Manter',
      destrutivo: true,
    });
    if (!confirmado) return;
    setExcluindo(simulacao.id);
    try {
      await acoes.excluirSimulacao(cliente.id, simulacao.id);
      avisar('Simulação excluída');
    } catch (falha) {
      avisar(
        falha instanceof ErroApi ? falha.message : 'Não foi possível excluir a simulação',
        'erro'
      );
    } finally {
      setExcluindo(null);
    }
  }

  return (
    <Tela folha={false}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.cabecalho}>
          <View style={styles.cabecalhoTopo}>
            <BotaoIcone icone="voltar" aoPressionar={() => router.back()} rotuloAcessivel="Voltar" escuro />
            <Pressable
              onPress={() => router.push(`/cliente/editar?id=${cliente.id}`)}
              accessibilityRole="button"
              accessibilityLabel={`Editar dados de ${cliente.nome}`}
              hitSlop={12}
              style={styles.editar}>
              <Icone nome="editar" tamanho={16} cor={cores.escuroTextoSecundario} />
              <Text style={styles.editarTexto}>Editar</Text>
            </Pressable>
          </View>

          <View style={styles.identidade}>
            <Avatar nome={cliente.nome} fotoUri={cliente.fotoUri} tamanho={64} quadrado />
            <View style={styles.flex}>
              <Text style={[textosEscuros.titulo]} accessibilityRole="header">
                {cliente.nome}
              </Text>
              <Text style={textosEscuros.apoio}>
                {cliente.telefone}
                {menor ? ` · ${idade} anos` : ''}
              </Text>
            </View>
          </View>

          {cliente.observacoes ? (
            <View style={styles.observacoes}>
              <Text style={textosEscuros.etiqueta}>Observações</Text>
              <Text style={[textosEscuros.corpo, styles.observacoesTexto]}>{cliente.observacoes}</Text>
            </View>
          ) : null}
        </View>

        <View style={styles.corpo}>
          {/* Iniciar simulação saiu daqui: a entrada é única, pelo botão fixo da barra
              inferior, que pede o cliente logo em seguida. Visualizar e comparar as
              simulações já salvas continua nesta tela, mais abaixo. */}
          <View style={styles.acoes}>
            <Botao
              titulo="Registrar atendimento"
              variante="secundaria"
              icone="registrar"
              aoPressionar={() => router.push(`/atendimento/novo?clienteId=${cliente.id}`)}
              estilo={styles.flex}
            />
          </View>

          {/* Consentimento de imagem — estado, ações e trilha de decisões. */}
          <Cartao estilo={styles.consentimento}>
            <View style={styles.consentimentoTopo}>
              <SeloConsentimento status={resumo.status} revalidar={resumo.revalidar} />
              {menor ? <Selo texto="menor de idade" tom="alerta" icone="alerta" /> : null}
            </View>

            <Text style={[textos.apoio, styles.consentimentoTexto]}>
              {textoDoConsentimento(resumo, cliente.nome)}
            </Text>

            {/* Uma ação só, escolhida pelo estado REGISTRADO do consentimento — não pela
                aparência da tela. Sem registro, a pendência é responder; havendo
                registro, a ação natural é consultar, e a tela do termo oferece
                registrar uma decisão nova a partir dali. Ausência de registro nunca é
                tratada como consentimento. */}
            <View style={styles.consentimentoAcoes}>
              {resumo.registro ? (
                <Botao
                  titulo="Ver termo"
                  variante="secundaria"
                  icone="documento"
                  aoPressionar={() => router.push(`/termo/${cliente.id}`)}
                  rotuloAcessivel="Ver o termo apresentado e a decisão registrada"
                  estilo={styles.flex}
                />
              ) : (
                <Botao
                  titulo="Responder ao termo"
                  variante="acao"
                  icone="documento"
                  aoPressionar={() => router.push(`/consentimento/${cliente.id}`)}
                  rotuloAcessivel="Apresentar o termo ao cliente e registrar a decisão dele"
                  estilo={styles.flex}
                />
              )}
            </View>

            {resumo.status === 'aceito' ? (
              <Botao
                titulo="Cancelar consentimento"
                variante="perigo"
                tamanho="pequeno"
                aoPressionar={revogar}
                estilo={styles.cancelar}
              />
            ) : null}

            {decisoes.length > 0 ? (
              <Pressable
                onPress={() => setVerDecisoes((v) => !v)}
                accessibilityRole="button"
                accessibilityState={{ expanded: verDecisoes }}
                style={styles.alternarDecisoes}>
                <Text style={textos.link}>
                  {verDecisoes ? 'Ocultar histórico de decisões' : `Histórico de decisões (${decisoes.length})`}
                </Text>
                <Icone nome="chevron" tamanho={14} cor={cores.acaoTexto} />
              </Pressable>
            ) : null}

            {verDecisoes ? (
              <View style={styles.decisoes}>
                {decisoes.map((registro) => (
                  <View key={registro.id} style={styles.registro}>
                    <Text style={styles.registroData}>{dataCurta(registro.registradoEm)}</Text>
                    <Text style={[textos.apoio, styles.flex]}>
                      {DECISAO[registro.decisao]} · versão {registro.versaoTermo} ·{' '}
                      {rotuloFormaObtencao(registro.formaObtencao)}
                      {registro.responsavel
                        ? `\nResponsável: ${registro.responsavel.nome} (${registro.responsavel.parentesco})`
                        : `\nConfirmado por ${registro.confirmadoPor}`}
                      {registro.observacao ? `\n“${registro.observacao}”` : ''}
                    </Text>
                  </View>
                ))}
              </View>
            ) : null}
          </Cartao>

          <View style={styles.tituloLinha}>
            <Text style={textos.secao}>Simulações salvas</Text>
            {simulacoes.length > 0 ? (
              <Text style={textos.meta}>
                {simulacoes.length} {simulacoes.length === 1 ? 'imagem' : 'imagens'}
              </Text>
            ) : null}
          </View>

          {simulacoes.length === 0 ? (
            <Cartao>
              <Text style={textos.apoio}>
                Nenhuma simulação guardada. A primeira aparece aqui assim que você gerar uma.
              </Text>
            </Cartao>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.galeria}>
              {simulacoes.map((s) => (
                <View key={s.id} style={styles.miniatura}>
                  <Pressable
                    onPress={() => router.push(`/simulacao/imagem/${s.id}`)}
                    accessibilityRole="button"
                    accessibilityLabel={`Abrir a simulação de ${diaMes(s.criadoEm)}, ${s.parametros.cor}${
                      s.preferida ? ', preferida' : ''
                    }`}
                    style={styles.miniaturaAbrir}>
                    <ImagemSimulada
                      uri={s.imgSaidaUri}
                      claro
                      legenda={s.status === 'processando' ? 'gerando…' : 'simulação'}
                      estilo={styles.miniaturaImagem}
                    />
                    <Text style={textos.meta}>{diaMes(s.criadoEm)}</Text>
                    <Text style={textos.apoioForte} numberOfLines={1}>
                      {s.parametros.cor}
                    </Text>
                  </Pressable>
                  <View>
                    {/* Só uma preferida por cliente: é uma escolha única, como um rádio. Só a
                        simulação concluída pode ser a preferida. */}
                    {s.status === 'concluida' ? (
                      <Pressable
                        onPress={() => marcarPreferida(s)}
                        disabled={preferindo !== null}
                        accessibilityRole="radio"
                        accessibilityState={{ selected: s.preferida, checked: s.preferida, busy: preferindo === s.id }}
                        // O `accessibilityState` não chega ao HTML na web; o atributo ARIA chega.
                        aria-checked={s.preferida}
                        accessibilityLabel={`Marcar ${s.parametros.cor} como preferida do cliente`}
                        style={({ pressed }) => [
                          styles.acaoMiniatura,
                          (pressed || preferindo === s.id) && styles.pressionado,
                        ]}>
                        <View style={[styles.radio, s.preferida && styles.radioAtivo]}>
                          {s.preferida ? <Icone nome="ok" tamanho={11} cor="#FFFFFF" /> : null}
                        </View>
                        <Text style={[styles.preferidaTexto, s.preferida && styles.preferidaAtiva]}>
                          {s.preferida ? 'Preferida' : 'Marcar como preferida'}
                        </Text>
                      </Pressable>
                    ) : null}
                    {/* Em geração não se exclui: o servidor ainda vai gravar o resultado. */}
                    {s.status !== 'processando' ? (
                      <Pressable
                        onPress={() => excluirSimulacao(s)}
                        disabled={excluindo !== null}
                        accessibilityRole="button"
                        accessibilityState={{ disabled: excluindo !== null, busy: excluindo === s.id }}
                        accessibilityLabel={`Excluir a simulação de ${diaMes(s.criadoEm)}, ${s.parametros.cor}`}
                        style={({ pressed }) => [
                          styles.acaoMiniatura,
                          (pressed || excluindo === s.id) && styles.pressionado,
                        ]}>
                        <Icone nome="excluir" tamanho={13} cor={cores.erroTexto} />
                        <Text style={styles.excluirTexto}>{excluindo === s.id ? 'Excluindo…' : 'Excluir'}</Text>
                      </Pressable>
                    ) : null}
                  </View>
                </View>
              ))}
            </ScrollView>
          )}

          {simulacoes.length > 0 ? (
            <Botao
              titulo="Comparar simulações"
              variante="secundaria"
              icone="comparar"
              aoPressionar={() => router.push(`/simulacao/comparar?clienteId=${cliente.id}`)}
              rotuloAcessivel={`Comparar duas simulações de ${cliente.nome} lado a lado`}
              estilo={styles.comparar}
            />
          ) : null}

          <Text style={[textos.secao, styles.tituloHistorico]}>Histórico de atendimentos</Text>
          {historico.length === 0 ? (
            <Cartao>
              <Text style={textos.apoio}>Nenhum atendimento registrado até agora.</Text>
            </Cartao>
          ) : (
            <View style={styles.lista}>
              {historico.map((h) => (
                <ItemHistorico key={h.id} item={h} />
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1 },
  ausente: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espaco.sm },
  cabecalho: {
    backgroundColor: cores.base,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.sm,
    paddingBottom: espaco.xl,
  },
  cabecalhoTopo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: espaco.lg,
  },
  editar: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm, minHeight: 44 },
  editarTexto: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 14,
    color: cores.escuroTextoSecundario,
  },
  identidade: { flexDirection: 'row', gap: espaco.lg, alignItems: 'center' },
  observacoes: {
    marginTop: espaco.lg,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    gap: espaco.xs,
  },
  observacoesTexto: { color: cores.escuroTextoSecundario },
  // Folha clara do conteúdo, logo abaixo do topo escuro.
  corpo: {
    flexGrow: 1,
    backgroundColor: cores.fundo,
    borderTopLeftRadius: raios.bloco,
    borderTopRightRadius: raios.bloco,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.xl,
    paddingBottom: espaco.xxxl,
  },
  acoes: { flexDirection: 'row', gap: espaco.sm },
  flex: { flex: 1 },
  consentimento: { marginTop: espaco.xl },
  consentimentoTopo: { flexDirection: 'row', gap: espaco.sm, flexWrap: 'wrap' },
  consentimentoTexto: { marginTop: espaco.md },
  consentimentoAcoes: {
    flexDirection: 'row',
    gap: espaco.lg,
    marginTop: espaco.sm,
    flexWrap: 'wrap',
  },
  // Centralizado no cartão do consentimento, com a largura do próprio texto.
  cancelar: { marginTop: espaco.sm, alignSelf: 'center', paddingHorizontal: espaco.lg },
  alternarDecisoes: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.xs,
    marginTop: espaco.md,
    minHeight: 44,
  },
  decisoes: {
    gap: espaco.md,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
    paddingTop: espaco.md,
  },
  registro: { flexDirection: 'row', gap: espaco.md },
  registroData: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 12,
    color: cores.textoApoio,
    minWidth: 68,
  },
  tituloLinha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: espaco.xxl,
    marginBottom: espaco.md,
  },
  galeria: { gap: espaco.md, paddingBottom: espaco.xs },
  // Na linha, as miniaturas têm a mesma altura: "Excluir" fica na base de todas, alinhado,
  // com ou sem o selo de preferida.
  miniatura: { width: 112, gap: espaco.xs, justifyContent: 'space-between' },
  miniaturaAbrir: { gap: espaco.xs },
  acaoMiniatura: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.xs,
    minHeight: ALVO_TOQUE,
  },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: cores.bordaForte,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioAtivo: { borderColor: cores.acao, backgroundColor: cores.acao },
  // Quebra a linha em vez de vazar da miniatura, que é estreita.
  preferidaTexto: { flex: 1, fontFamily: fontes.sansMedio, fontSize: 13, color: cores.texto },
  preferidaAtiva: { fontFamily: fontes.sansSemi, color: cores.acaoTexto },
  excluirTexto: { fontFamily: fontes.sansSemi, fontSize: 13, color: cores.erroTexto },
  pressionado: { opacity: 0.6 },
  miniaturaImagem: { height: 140 },
  comparar: { marginTop: espaco.md },
  tituloHistorico: { marginTop: espaco.xxl, marginBottom: espaco.md },
  lista: { gap: espaco.sm },
});
