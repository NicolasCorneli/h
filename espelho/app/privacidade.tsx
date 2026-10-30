import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Cartao, Etiqueta, Grupo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { useFeedback } from '@/components/Feedback';
import { useStore } from '@/data/store';
import type { ConsentimentoStatus } from '@/data/tipos';
import { USO_DE_DADOS } from '@/data/servicoExterno';
import { ErroApi } from '@/services/api';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, hora } from '@/utils/datas';

const GARANTIAS = [
  {
    titulo: 'Criptografia',
    texto:
      'As imagens não têm endereço público: cada uma abre por um link assinado que expira em poucos minutos. Em produção, o tráfego usa TLS e o armazenamento, criptografia em repouso.',
  },
  {
    titulo: 'O que vai para o serviço externo',
    texto: `${USO_DE_DADOS.oQueSai} ${USO_DE_DADOS.consentimento}`,
  },
  {
    titulo: 'O que a outra empresa pode fazer com a imagem',
    texto: `${USO_DE_DADOS.oQueElaPodeFazer} ${USO_DE_DADOS.oQueNaoControlamos} É isso que o termo do cliente informa, com estas palavras, antes de ele decidir.`,
  },
  {
    titulo: 'Retenção',
    texto:
      'As simulações ficam guardadas na sua conta enquanto o cliente existir na sua carteira, ou até você excluí-las. Excluir o cliente ou a conta apaga tudo em cascata.',
  },
];

/** Art. 18 da LGPD como interface: consentimentos, retenção e exclusões com escopo claro. */
export default function Privacidade() {
  const router = useRouter();
  const { estado, acoes } = useStore();
  const { confirmar, avisar } = useFeedback();
  const imagens = estado.simulacoes.filter((s) => s.imgSaidaUri || s.imgEntradaUri).length;

  const porStatus = estado.clientes.reduce(
    (contagem, cliente) => {
      contagem[cliente.consentimento.status] += 1;
      return contagem;
    },
    { aceito: 0, pendente: 0, recusado: 0, revogado: 0 } as Record<ConsentimentoStatus, number>
  );

  async function excluirImagens() {
    const ok = await confirmar({
      titulo: 'Excluir imagens de simulação?',
      mensagem:
        'Apaga as simulações de todos os clientes, as fotos originais e também as fotos de perfil. ' +
        'Clientes, histórico de atendimentos, agenda e registros de consentimento continuam intactos.',
      rotuloConfirmar: 'Excluir imagens',
      destrutivo: true,
    });
    if (!ok) return;
    try {
      await acoes.excluirImagens();
      avisar('Imagens apagadas');
    } catch (falha) {
      avisar(
        falha instanceof ErroApi ? falha.message : 'Não foi possível excluir as imagens',
        'erro'
      );
    }
  }

  /**
   * A exclusão da conta é irreversível e pede a senha outra vez, em tela própria — o
   * servidor recusa a operação sem ela.
   */
  function irParaExclusaoDaConta() {
    router.push('/excluir-conta');
  }

  const ciencia = estado.cienciaProfissional;

  return (
    <Tela>
      <Cabecalho
        titulo="Privacidade e meus dados"
        subtitulo="LGPD · art. 18"
        aoVoltar={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        {ciencia.aceita && ciencia.registradaEm ? (
          <Aviso
            tom="sucesso"
            titulo="Ciência das responsabilidades aceita"
            texto={`Registrada em ${dataCurta(ciencia.registradaEm)}, às ${hora(
              ciencia.registradaEm
            )}. Ela é sua, não do cliente: o consentimento de imagem fica no perfil de cada um.`}>
            <Botao
              titulo="Reler minhas responsabilidades"
              variante="texto"
              larguraTotal={false}
              aoPressionar={() => router.push('/responsabilidades')}
            />
          </Aviso>
        ) : (
          <Aviso
            tom="alerta"
            titulo="Ciência das responsabilidades pendente"
            texto="Leia o que precisa ser explicado ao cliente antes de registrar qualquer consentimento.">
            <Botao
              titulo="Ler agora"
              variante="texto"
              larguraTotal={false}
              aoPressionar={() => router.push('/responsabilidades')}
            />
          </Aviso>
        )}

        <Etiqueta estilo={styles.etiqueta}>Consentimento dos clientes</Etiqueta>
        <Cartao>
          <Text style={textos.apoio}>
            Cada cliente decide sobre a própria imagem. O aceite, a recusa e o cancelamento ficam
            registrados no perfil dele.
          </Text>
          <View style={styles.contagens}>
            <Contagem numero={porStatus.aceito} rotulo="autorizaram" />
            <Contagem numero={porStatus.pendente} rotulo="pendentes" />
            <Contagem numero={porStatus.recusado + porStatus.revogado} rotulo="bloqueados" />
          </View>
          <Botao
            titulo="Abrir a lista de clientes"
            variante="texto"
            icone="clientes"
            larguraTotal={false}
            aoPressionar={() => router.push('/(tabs)/clientes')}
          />
        </Cartao>

        <Etiqueta estilo={styles.etiqueta}>Como seus dados ficam</Etiqueta>
        <Grupo>
          {GARANTIAS.map((g) => (
            <View key={g.titulo} style={styles.garantia}>
              <Text style={textos.corpoForte}>{g.titulo}</Text>
              <Text style={textos.apoio}>{g.texto}</Text>
            </View>
          ))}
        </Grupo>

        <Etiqueta estilo={styles.etiqueta}>Exclusão</Etiqueta>
        <View style={styles.caixaPerigo}>
          <Text style={textos.corpoForte}>Excluir todas as imagens de simulação</Text>
          <Text style={[textos.apoio, styles.perigoTexto]}>
            {imagens === 0
              ? 'Nenhuma imagem guardada na sua conta.'
              : `Apaga ${imagens} ${
                  imagens === 1 ? 'simulação' : 'simulações'
                } e as fotos correspondentes do armazenamento, inclusive as fotos de perfil dos clientes. Cadastros, histórico, agenda e consentimentos continuam intactos.`}
          </Text>
          <Botao
            titulo="Excluir imagens"
            variante="perigo"
            tamanho="medio"
            icone="excluir"
            desabilitado={imagens === 0}
            dicaAcessivel={imagens === 0 ? 'Não há imagens para excluir' : undefined}
            aoPressionar={excluirImagens}
          />
        </View>

        <View style={styles.caixaPerigo}>
          <Text style={textos.corpoForte}>Excluir minha conta e todos os dados</Text>
          <Text style={[textos.apoio, styles.perigoTexto]}>
            Remove conta, {estado.clientes.length}{' '}
            {estado.clientes.length === 1 ? 'cliente' : 'clientes'}, histórico, agenda,
            consentimentos e imagens. A ação é irreversível.
          </Text>
          <Botao
            titulo="Excluir conta"
            variante="perigo"
            tamanho="medio"
            icone="excluir"
            aoPressionar={irParaExclusaoDaConta}
          />
        </View>

        <Text style={[textos.meta, styles.nota]}>
          A exclusão remove os arquivos do armazenamento e os registros do banco de dados na
          hora, conforme o art. 18 da Lei nº 13.709/2018.
        </Text>
      </ScrollView>
    </Tela>
  );
}

function Contagem({ numero, rotulo }: { numero: number; rotulo: string }) {
  return (
    <View style={styles.contagem}>
      <Text style={textos.numero}>{numero}</Text>
      <Text style={textos.meta}>{rotulo}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxl },
  etiqueta: { marginTop: espaco.xl, marginBottom: espaco.sm },
  contagens: { flexDirection: 'row', gap: espaco.sm, marginVertical: espaco.md },
  contagem: {
    flex: 1,
    backgroundColor: cores.fundo,
    borderRadius: raios.campo,
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.md,
  },
  garantia: { backgroundColor: cores.superficie, padding: espaco.lg, gap: espaco.xs },
  caixaPerigo: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.erroBorda,
    borderRadius: raios.cartao,
    padding: espaco.lg,
    marginBottom: espaco.md,
    gap: espaco.xs,
  },
  perigoTexto: { marginBottom: espaco.md },
  nota: { marginTop: espaco.md },
});
