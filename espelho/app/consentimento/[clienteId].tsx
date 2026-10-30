import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Cartao, Etiqueta, Tela } from '@/components/Basicos';
import { Cabecalho } from '@/components/Cabecalho';
import { Campo } from '@/components/Campo';
import { useFeedback } from '@/components/Feedback';
import { Icone } from '@/components/Icone';
import { DocumentoTermo } from '@/components/DocumentoTermo';
import { SeloConsentimento } from '@/components/SeloConsentimento';
import { useCliente, useResumoConsentimento, useStore } from '@/data/store';
import type { FormaObtencao } from '@/data/tipos';
import { ErroApi } from '@/services/api';
import { exigeResponsavel, faixaEtaria, FORMAS_OBTENCAO, idadeEm } from '@/services/consentService';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta } from '@/utils/datas';

/**
 * Termo de uso de imagem apresentado ao CLIENTE e registro da decisão dele.
 *
 * "Aceitar" e "Recusar" têm o mesmo peso visual: tamanho, tipografia e destaque
 * equivalentes. Induzir o aceite com um botão maior comprometeria o requisito de
 * consentimento livre (LGPD, art. 5º, XII).
 */
export default function TermoDoCliente() {
  const { clienteId, retorno } = useLocalSearchParams<{ clienteId: string; retorno?: string }>();
  const router = useRouter();
  const { acoes } = useStore();
  const { avisar } = useFeedback();
  const cliente = useCliente(clienteId);
  const resumo = useResumoConsentimento(clienteId);

  const menor = exigeResponsavel(cliente);
  const idade = idadeEm(cliente?.dataNascimento ?? null);

  const [confirmadoPor, setConfirmadoPor] = useState('');
  const [responsavelNome, setResponsavelNome] = useState(resumo.registro?.responsavel?.nome ?? '');
  const [parentesco, setParentesco] = useState(resumo.registro?.responsavel?.parentesco ?? '');
  const [forma, setForma] = useState<FormaObtencao>('tela_dispositivo');
  const [observacao, setObservacao] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [documentoPronto, setDocumentoPronto] = useState(false);
  const [registrando, setRegistrando] = useState(false);

  if (!cliente) {
    return (
      <Tela>
        <Cabecalho titulo="Termo de uso de imagem" aoVoltar={() => router.back()} />
        <View style={styles.ausente}>
          <Text style={textos.corpo}>Cliente não encontrado.</Text>
        </View>
      </Tela>
    );
  }

  /**
   * A versão do termo **não** é enviada: quem define é o servidor, a partir da versão
   * vigente. Assim um aplicativo desatualizado não registra aceite sobre texto antigo.
   */
  async function registrar(decisao: 'aceito' | 'recusado') {
    if (!cliente || registrando) return;

    const nomeConfirmou = confirmadoPor.trim() || (menor ? responsavelNome.trim() : cliente.nome);
    if (menor && (!responsavelNome.trim() || !parentesco.trim())) {
      setErro('Para cliente menor de 18 anos, informe o nome e o parentesco do responsável legal.');
      avisar('Falta identificar o responsável legal', 'erro');
      return;
    }
    if (!nomeConfirmou) {
      setErro('Informe quem confirmou a decisão.');
      return;
    }

    setErro(null);
    setRegistrando(true);
    try {
      await acoes.registrarConsentimento(cliente.id, {
        decisao,
        formaObtencao: forma,
        confirmadoPor: nomeConfirmou,
        responsavel: menor ? { nome: responsavelNome.trim(), parentesco: parentesco.trim() } : null,
        observacao: observacao.trim(),
      });

      avisar(decisao === 'aceito' ? 'Consentimento registrado' : 'Recusa registrada');

      if (decisao === 'aceito' && retorno === 'captura') {
        router.replace('/simulacao/captura');
        return;
      }
      router.replace(`/cliente/${cliente.id}`);
    } catch (falha) {
      const apiErro = falha instanceof ErroApi ? falha : null;
      setErro(apiErro?.message ?? 'Não foi possível registrar a decisão agora.');
      avisar(apiErro?.message ?? 'Não foi possível registrar a decisão', 'erro');
    } finally {
      setRegistrando(false);
    }
  }

  return (
    <Tela>
      <Cabecalho
        titulo="Termo de uso de imagem"
        subtitulo={cliente.nome}
        aoVoltar={() => router.back()}
        iconeVoltar="fechar"
      />

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
        keyboardVerticalOffset={20}>
        <ScrollView
          contentContainerStyle={styles.conteudo}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          {resumo.status !== 'pendente' ? (
            <Cartao estilo={styles.estadoAtual}>
              <SeloConsentimento status={resumo.status} revalidar={resumo.revalidar} />
              {resumo.registro ? (
                <Text style={textos.apoio}>
                  Última decisão em {dataCurta(resumo.registro.registradoEm)}, sobre a versão{' '}
                  {resumo.registro.versaoTermo} do termo.
                </Text>
              ) : null}
            </Cartao>
          ) : null}

          {menor ? (
            <Aviso
              tom="alerta"
              titulo={
                faixaEtaria(cliente) === 'crianca'
                  ? 'Criança: consentimento específico do responsável'
                  : 'Menor de 18 anos: quem consente é o responsável'
              }
              texto={`${cliente.nome} tem ${idade} anos. A decisão precisa ser dada por um dos pais ou pelo responsável legal, presente neste momento (LGPD, art. 14).`}
            />
          ) : null}

          {/* Documento: texto somente leitura, vindo do servidor, nunca em campo editável. */}
          <DocumentoTermo
            tipo="cliente"
            estilo={styles.termo}
            aoMudarDisponibilidade={setDocumentoPronto}
          />

          <Etiqueta estilo={styles.etiqueta}>Registro da decisão</Etiqueta>

          {menor ? (
            <View style={styles.campos}>
              <Campo
                rotulo="Nome do responsável legal"
                obrigatorio
                valor={responsavelNome}
                aoMudar={setResponsavelNome}
                placeholder="Denise Ramires"
                autoCapitalize="words"
              />
              <Campo
                rotulo="Parentesco"
                obrigatorio
                valor={parentesco}
                aoMudar={setParentesco}
                placeholder="Mãe, pai, tutor…"
                autoCapitalize="words"
              />
            </View>
          ) : null}

          <Campo
            rotulo="Quem confirmou a decisão"
            valor={confirmadoPor}
            aoMudar={setConfirmadoPor}
            placeholder={menor ? responsavelNome || 'Nome do responsável' : cliente.nome}
            autoCapitalize="words"
            ajuda={`Peça para a pessoa digitar o próprio nome. Em branco, fica registrado ${
              menor ? 'o nome do responsável' : `“${cliente.nome}”`
            }.`}
            estilo={styles.campo}
          />

          <Text style={[textos.corpoForte, styles.subtitulo]}>Como o termo foi apresentado</Text>
          <View style={styles.formas}>
            {FORMAS_OBTENCAO.map((f) => {
              const ativo = forma === f.valor;
              return (
                <Pressable
                  key={f.valor}
                  onPress={() => setForma(f.valor)}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: ativo }}
                  accessibilityLabel={f.rotulo}
                  accessibilityHint={f.descricao}
                  style={[styles.forma, ativo && styles.formaAtiva]}>
                  <View style={[styles.radio, ativo && styles.radioAtivo]}>
                    {ativo ? <Icone nome="ok" tamanho={12} cor="#FFFFFF" /> : null}
                  </View>
                  <View style={styles.flex}>
                    <Text style={textos.apoioForte}>{f.rotulo}</Text>
                    <Text style={textos.meta}>{f.descricao}</Text>
                  </View>
                </Pressable>
              );
            })}
          </View>

          <Campo
            rotulo="Observação (opcional)"
            valor={observacao}
            aoMudar={setObservacao}
            placeholder="Algo que o cliente pediu para constar"
            multilinha
            estilo={styles.campo}
            erro={erro}
          />
        </ScrollView>

        {/* Decisão: os dois caminhos têm o mesmo peso visual. */}
        <View style={styles.rodape}>
          <View style={styles.decisao}>
            <Pressable
              onPress={() => void registrar('recusado')}
              disabled={!documentoPronto || registrando}
              accessibilityRole="button"
              accessibilityState={{ disabled: !documentoPronto || registrando }}
              accessibilityLabel="Registrar que o cliente recusou o uso da imagem"
              accessibilityHint={
                !documentoPronto ? 'Aguarde o texto do termo carregar' : undefined
              }
              style={({ pressed }) => [
                styles.botaoDecisao,
                styles.botaoRecusa,
                pressed && styles.pressionado,
                (!documentoPronto || registrando) && styles.desabilitado,
              ]}>
              <Icone nome="proibido" tamanho={18} cor={cores.erroTexto} />
              <Text style={[styles.decisaoTexto, { color: cores.erroTexto }]}>Recusou</Text>
            </Pressable>

            <Pressable
              onPress={() => void registrar('aceito')}
              disabled={!documentoPronto || registrando}
              accessibilityRole="button"
              accessibilityState={{ disabled: !documentoPronto || registrando }}
              accessibilityLabel="Registrar que o cliente aceitou o uso da imagem"
              accessibilityHint={
                !documentoPronto ? 'Aguarde o texto do termo carregar' : undefined
              }
              style={({ pressed }) => [
                styles.botaoDecisao,
                styles.botaoAceite,
                pressed && styles.pressionado,
                (!documentoPronto || registrando) && styles.desabilitado,
              ]}>
              <Icone nome="okCirculo" tamanho={18} cor={cores.sucessoTexto} />
              <Text style={[styles.decisaoTexto, { color: cores.sucessoTexto }]}>Aceitou</Text>
            </Pressable>
          </View>

          <Text style={[textos.meta, styles.nota]}>
            Recusar não afeta cadastro, histórico nem agenda deste cliente.
          </Text>
        </View>
      </KeyboardAvoidingView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  ausente: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xl },
  estadoAtual: { gap: espaco.sm, marginBottom: espaco.md },
  termo: { marginTop: espaco.lg },
  etiqueta: { marginTop: espaco.xxl, marginBottom: espaco.md },
  campos: { gap: espaco.md, marginBottom: espaco.md },
  campo: { marginTop: espaco.xs },
  subtitulo: { marginTop: espaco.xl, marginBottom: espaco.md },
  formas: { gap: espaco.sm },
  forma: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    paddingHorizontal: espaco.lg,
    paddingVertical: espaco.md,
    minHeight: 60,
  },
  formaAtiva: { borderColor: cores.acao, borderWidth: 2 },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.5,
    borderColor: cores.bordaForte,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioAtivo: { borderColor: cores.acao, backgroundColor: cores.acao },
  rodape: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
    backgroundColor: cores.fundo,
  },
  decisao: { flexDirection: 'row', gap: espaco.md },
  botaoDecisao: {
    flex: 1,
    height: 56,
    borderRadius: raios.campo,
    borderWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espaco.sm,
  },
  botaoRecusa: { backgroundColor: cores.erroFundo, borderColor: cores.erroBorda },
  botaoAceite: { backgroundColor: cores.sucessoFundo, borderColor: cores.sucessoBorda },
  decisaoTexto: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 16 },
  nota: { textAlign: 'center', marginTop: espaco.md },
  pressionado: { opacity: 0.85 },
  desabilitado: { opacity: 0.5 },
});
