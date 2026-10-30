import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { Icone } from '@/components/Icone';
import { useRascunho } from '@/data/rascunho';
import { useStore } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { rotuloCor, rotuloCorte } from '@/utils/pedido';

type Motivo = { titulo: string; texto: string; repetir: boolean };

/**
 * O que dizer para cada motivo de falha. O código vem do servidor: da simulação que falhou
 * (`erroCodigo`) ou do envio que nem chegou a criar uma (`falhaEnvio`).
 */
const MOTIVOS: Record<string, Motivo> = {
  credencial_ausente: {
    titulo: 'O serviço de IA não está configurado',
    texto: 'O servidor está sem a chave do serviço de simulação (AI_API_KEY). Configure a chave e reinicie o servidor.',
    repetir: false,
  },
  credencial_invalida: {
    titulo: 'A chave do serviço de IA foi recusada',
    texto: 'Confira a AI_API_KEY no servidor: ela pode ter sido revogada ou copiada com espaço ou aspas a mais.',
    repetir: false,
  },
  sem_credito: {
    titulo: 'Sem crédito no serviço de IA',
    texto: 'A conta do serviço de simulação está sem saldo. Adicione crédito e tente de novo.',
    repetir: true,
  },
  limite_do_provedor: {
    titulo: 'O serviço de IA está ocupado',
    texto: 'Ele recebeu pedidos demais agora. Espere um minuto e tente de novo.',
    repetir: true,
  },
  limite_de_simulacoes: {
    titulo: 'Limite de simulações atingido',
    texto: '',
    repetir: false,
  },
  timeout: {
    titulo: 'A geração demorou demais',
    texto: 'O serviço não terminou no tempo esperado. Tente de novo; se repetir, tente mais tarde.',
    repetir: true,
  },
  tempo_esgotado: {
    titulo: 'A geração está demorando',
    texto: 'O aparelho parou de esperar, mas a simulação pode terminar no servidor e aparecer no histórico do cliente.',
    repetir: true,
  },
  parou_de_esperar: {
    titulo: 'Você parou de esperar',
    texto: 'A geração continua no servidor e aparece no histórico do cliente quando terminar. "Tentar novamente" volta a acompanhar a mesma simulação, sem gerar outra.',
    repetir: true,
  },
  conteudo_bloqueado: {
    titulo: 'O filtro de segurança recusou o pedido',
    texto: 'O serviço de IA bloqueou a imagem pelo filtro de segurança dele. Tente outra foto ou outra descrição.',
    repetir: true,
  },
  falha_na_geracao: {
    titulo: 'O serviço não conseguiu gerar a imagem',
    texto: 'Tente de novo. Se repetir, mude a descrição ou use outra foto.',
    repetir: true,
  },
  resposta_invalida: {
    titulo: 'O serviço devolveu um resultado inutilizável',
    texto: 'A geração terminou sem uma imagem válida. Tente de novo.',
    repetir: true,
  },
  entrada_recusada: {
    titulo: 'O serviço recusou os parâmetros',
    texto: 'O modelo não aceitou o que o sistema enviou. Na pasta backend, rode "python -m app.diagnostico_ia" para conferir a configuração.',
    repetir: false,
  },
  modelo_incompativel: {
    titulo: 'O modelo configurado não é compatível',
    texto: 'O schema publicado do modelo não tem os campos que o sistema usa. Rode "python -m app.diagnostico_ia" na pasta backend.',
    repetir: false,
  },
  parametro_fora_do_schema: {
    titulo: 'Opção fora do que o modelo aceita',
    texto: 'Rode "python -m app.diagnostico_ia" na pasta backend para ver as opções publicadas do modelo.',
    repetir: false,
  },
  modelo_inexistente: {
    titulo: 'Modelo não encontrado no serviço de IA',
    texto: 'Confira os nomes em AI_MODELO e AI_MODELO_TEXTO no servidor.',
    repetir: false,
  },
  sem_conexao: {
    titulo: 'Sem conexão com o servidor',
    texto: 'Confira a internet e tente de novo. Se o servidor tiver recebido o pedido, a nova tentativa retoma a mesma simulação.',
    repetir: true,
  },
  interrompida: {
    titulo: 'A geração foi interrompida',
    texto: 'O servidor reiniciou durante a geração. Tente de novo.',
    repetir: true,
  },
};

const PADRAO: Motivo = {
  titulo: 'O serviço de simulação não respondeu',
  texto: 'O problema está no serviço que gera as simulações, não no seu aparelho.',
  repetir: true,
};

/** Degradação graciosa (seção 5.12): a gestão segue funcionando sem o provedor de IA. */
export default function IaIndisponivel() {
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);
  const simulacao = estado.simulacoes.find((s) => s.id === rascunho.simulacaoId);

  const codigo = rascunho.falhaEnvio?.codigo ?? simulacao?.erroCodigo ?? 'desconhecido';
  const motivo = MOTIVOS[codigo] ?? PADRAO;
  const texto = codigo === 'limite_de_simulacoes' ? (rascunho.falhaEnvio?.mensagem ?? '') : motivo.texto;
  const escolhas = {
    corte: rascunho.corte,
    manterCorte: rascunho.manterCorte,
    cor: rascunho.cor,
    manterCor: rascunho.manterCor,
  };

  return (
    <Tela>
      <Cabecalho titulo="Simulação" aoVoltar={() => router.back()} comLinha={false} />

      <ScrollView contentContainerStyle={styles.conteudo}>
        <View style={styles.icone}>
          <Icone nome="alerta" tamanho={24} cor={cores.erroTexto} />
        </View>

        <Text style={[textos.display, styles.titulo]} accessibilityRole="header">
          {motivo.titulo}
        </Text>
        {texto ? <Text style={[textos.corpo, styles.texto]}>{texto}</Text> : null}

        <Text style={[textos.meta, styles.texto]}>
          A foto e as escolhas continuam guardadas aqui: corte “{rotuloCorte(escolhas)}”, cor “
          {rotuloCor(escolhas)}”.
        </Text>
        {simulacao?.erroCodigo ? (
          <Text style={[textos.meta, styles.texto]}>
            A tentativa ficou registrada no histórico como não concluída (motivo: {simulacao.erroCodigo}).
          </Text>
        ) : null}

        <Aviso
          tom="sucesso"
          texto="Clientes, histórico e agenda seguem funcionando normalmente: eles não dependem da simulação."
        />

        {motivo.repetir ? (
          <Botao
            titulo="Tentar novamente"
            icone="trocarCamera"
            aoPressionar={() => {
              // Depois de uma falha registrada, a nova tentativa é uma simulação nova. Sem
              // conexão ou parada de espera, a chave fica e o servidor retoma a mesma.
              atualizar({ simulacaoId: null, falhaEnvio: null, demoFalharIa: false });
              router.replace('/simulacao/processando');
            }}
            estilo={styles.botao}
          />
        ) : null}
        <Botao
          titulo="Mudar o pedido"
          variante={motivo.repetir ? 'secundaria' : 'primaria'}
          icone="editar"
          aoPressionar={() => {
            atualizar({ simulacaoId: null, falhaEnvio: null, demoFalharIa: false });
            router.dismissTo('/simulacao/parametros');
          }}
          estilo={motivo.repetir ? styles.botaoSeguinte : styles.botao}
        />
        <Botao
          titulo={cliente ? `Voltar ao perfil de ${cliente.nome.split(' ')[0]}` : 'Voltar ao início'}
          variante="texto"
          aoPressionar={() => router.replace(cliente ? `/cliente/${cliente.id}` : '/(tabs)')}
        />
      </ScrollView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  conteudo: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: espaco.xl,
    paddingVertical: espaco.xxl,
  },
  icone: {
    width: 52,
    height: 52,
    borderRadius: raios.cartao,
    backgroundColor: cores.erroFundo,
    borderWidth: 1,
    borderColor: cores.erroBorda,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espaco.xl,
  },
  titulo: { marginBottom: espaco.md },
  texto: { marginBottom: espaco.lg },
  botao: { marginTop: espaco.xxl },
  botaoSeguinte: { marginTop: espaco.sm },
});
