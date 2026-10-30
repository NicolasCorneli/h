import { useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AvisoDeConexao, useFalhouAoCarregar } from '@/components/AvisoDeConexao';
import { Avatar, Faixa, Aviso, Cartao, Esqueleto, Selo, Tela } from '@/components/Basicos';
import { EstadoVazio } from '@/components/EstadoVazio';
import { Icone } from '@/components/Icone';
import { useAtualizar } from '@/components/Atualizar';
import { STATUS_CURTO, STATUS_LABEL, useAgendamentosOrdenados, useStore } from '@/data/store';
import { TOM_STATUS } from '@/theme/status';
import { compromissosDeHoje, horariosAgendados, simulacoesDeHoje } from '@/utils/painel';
import { textos, textosEscuros } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { diaPorExtenso, distanciaAteAgora, hora, mesmoDia, saudacao } from '@/utils/datas';

/** T2 — dashboard organizado por urgência: o próximo atendimento manda na tela. */
export default function Dashboard() {
  const router = useRouter();
  const { controle } = useAtualizar();
  const { estado, carregando } = useStore();
  const agendamentos = useAgendamentosOrdenados();
  const agoraIso = new Date().toISOString();

  // Só o que ainda está em aberto: concluídos e cancelados já não são "ainda hoje".
  const doDia = compromissosDeHoje(agendamentos);
  // O próximo é o que ainda vai acontecer: nem cancelado, nem já concluído.
  const proximo = agendamentos.find(
    (a) => a.dataHora >= agoraIso && (a.status === 'pendente' || a.status === 'confirmado')
  );
  const clienteDoProximo = estado.clientes.find((c) => c.id === proximo?.clienteId);
  const simulacoesHoje = simulacoesDeHoje(estado.simulacoes);
  // Horários em aberto de hoje em diante, um por agendamento, como na agenda (antes
  // contava clientes distintos, e a mesma cliente com dois horários contava um).
  const agendados = horariosAgendados(agendamentos);
  const falhou = useFalhouAoCarregar();
  // "Primeiro uso" é uma afirmação sobre a conta. Com a carga falhada não se sabe se a
  // carteira está vazia ou apenas inalcançável — e convidar a cadastrar o primeiro
  // cliente, nesse caso, é levar o profissional a duplicar o que já existe.
  const primeiroUso = estado.clientes.length === 0 && !falhou;

  const cabecalho = (
    <Faixa estilo={styles.cabecalho}>
      <View style={styles.flex}>
        <Text style={textosEscuros.meta}>{diaPorExtenso(agoraIso)}</Text>
        <Text style={[textosEscuros.titulo, styles.saudacao]} accessibilityRole="header">
          {primeiroUso ? 'Boas-vindas' : saudacao()}
          {estado.usuario ? `, ${estado.usuario.nome.split(' ')[0]}` : ''}
        </Text>
      </View>
      <Pressable
        onPress={() => router.push('/(tabs)/perfil')}
        accessibilityRole="button"
        accessibilityLabel="Abrir meu perfil"
        hitSlop={8}>
        <Avatar nome={estado.usuario?.nome ?? '?'} fotoUri={estado.usuario?.fotoUri} cor={cores.acao} tamanho={44} />
      </Pressable>
    </Faixa>
  );

  if (carregando) {
    return (
      <Tela>
        {cabecalho}
        <ScrollView contentContainerStyle={styles.conteudo} refreshControl={controle}>
          <Esqueleto altura={150} estilo={styles.esqueletoBloco} />
          <View style={styles.numeros}>
            <Esqueleto altura={72} estilo={styles.flex} />
            <Esqueleto altura={72} estilo={styles.flex} />
            <Esqueleto altura={72} estilo={styles.flex} />
          </View>
          <Esqueleto altura={72} estilo={styles.esqueletoBloco} />
        </ScrollView>
      </Tela>
    );
  }

  if (falhou && estado.clientes.length === 0) {
    return (
      <Tela>
        {cabecalho}
        <ScrollView contentContainerStyle={styles.conteudo} refreshControl={controle}>
          <AvisoDeConexao />
        </ScrollView>
      </Tela>
    );
  }

  if (primeiroUso) {
    return (
      <Tela>
        {cabecalho}
        <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
          <EstadoVazio
            icone="clientes"
            titulo="Sua carteira começa aqui"
            texto="Cadastre um cliente para poder salvar simulações, histórico e agendamentos no nome dele."
            acao={{ titulo: 'Cadastrar primeiro cliente', aoPressionar: () => router.push('/cliente/editar') }}
            compacto
          />
          <Aviso
            tom="neutro"
            texto="Clientes, histórico e agenda funcionam mesmo quando o serviço de simulação está fora do ar."
          />
        </ScrollView>
      </Tela>
    );
  }

  return (
    <Tela>
      {cabecalho}
      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>

        <AvisoDeConexao />

        {proximo && clienteDoProximo ? (
          // Uma ação só, e é o cartão inteiro: abrir o perfil do cliente. Simular e
          // registrar saíram daqui — a simulação tem entrada fixa na barra inferior, e
          // registrar atendimento vive no perfil, onde há contexto para decidir.
          <Pressable
            onPress={() => router.push(`/cliente/${clienteDoProximo.id}`)}
            accessibilityRole="button"
            accessibilityLabel={`Próximo atendimento: ${diaPorExtenso(proximo.dataHora)}, às ${hora(proximo.dataHora)}, ${clienteDoProximo.nome}, ${proximo.servico}. Abrir o perfil`}
            style={({ pressed }) => [styles.cartaoEscuro, pressed && styles.pressionado]}>
            <Text style={textosEscuros.etiqueta}>Próximo atendimento</Text>
            <Text style={[textosEscuros.corpo, styles.dataProximo]}>{dataDoProximo(proximo.dataHora)}</Text>
            <View style={styles.linhaHora}>
              <Text style={styles.horaGrande}>{hora(proximo.dataHora)}</Text>
              <Text style={[textosEscuros.corpo, styles.distancia]}>
                {distanciaAteAgora(proximo.dataHora)}
              </Text>
            </View>

            <View style={styles.linhaCliente}>
              <Avatar nome={clienteDoProximo.nome} fotoUri={clienteDoProximo.fotoUri} tamanho={40} />
              <View style={styles.flex}>
                <Text style={[textosEscuros.corpo, styles.nomeEscuro]}>{clienteDoProximo.nome}</Text>
                <Text style={textosEscuros.apoio}>{proximo.servico}</Text>
              </View>
            </View>

            <View style={styles.abrirPerfil}>
              <Text style={textosEscuros.apoio}>Ver perfil do cliente</Text>
              <Icone nome="avancar" tamanho={16} cor={cores.escuroTextoApoio} />
            </View>
          </Pressable>
        ) : (
          <Cartao estilo={styles.semProximo}>
            <Text style={textos.corpoForte}>Nenhum atendimento à frente</Text>
            <Text style={[textos.apoio, styles.semProximoTexto]}>
              Sua agenda está livre a partir de agora.
            </Text>
          </Cartao>
        )}

        <View style={styles.numeros}>
          <Numero valor={estado.clientes.length} rotulo="clientes" />
          <Numero valor={simulacoesHoje} rotulo="simulações hoje" />
          <Numero
            valor={agendados}
            rotulo="agendados"
            rotuloAcessivel={`${agendados} ${agendados === 1 ? 'horário marcado' : 'horários marcados'}, de hoje em diante`}
          />
        </View>

        {/* "Ver agenda" saiu: a aba Agenda já está fixa na barra inferior. Sem o botão,
            a linha com dois elementos virou um título simples. */}
        <Text style={[textos.secao, styles.tituloSecao]}>Ainda hoje</Text>

        {doDia.length === 0 ? (
          <Cartao>
            <Text style={textos.apoio}>Nenhum compromisso para hoje.</Text>
          </Cartao>
        ) : (
          <View style={styles.lista}>
            {doDia.map((a) => {
              const cliente = estado.clientes.find((c) => c.id === a.clienteId);
              return (
                <Cartao
                  key={a.id}
                  aoPressionar={cliente ? () => router.push(`/cliente/${cliente.id}`) : undefined}
                  rotuloAcessivel={
                    cliente
                      ? `${hora(a.dataHora)}, ${cliente.nome}, ${a.servico}. ${STATUS_LABEL[a.status]}`
                      : undefined
                  }
                  estilo={styles.itemAgenda}>
                  <Text style={styles.horaItem}>{hora(a.dataHora)}</Text>
                  <View style={styles.flex}>
                    <Text style={textos.corpoForte} numberOfLines={1}>
                      {cliente?.nome ?? 'Cliente removido'}
                    </Text>
                    <Text style={textos.apoio} numberOfLines={1}>
                      {a.servico}
                    </Text>
                  </View>
                  <Selo
                    texto={STATUS_CURTO[a.status]}
                    tom={TOM_STATUS[a.status].selo}
                    icone={TOM_STATUS[a.status].icone}
                  />
                </Cartao>
              );
            })}
          </View>
        )}
      </ScrollView>
    </Tela>
  );
}

/** "Hoje, sábado, 24 de outubro" / "Amanhã, ..." / "Quarta, 28 de outubro". */
function dataDoProximo(iso: string): string {
  const dia = diaPorExtenso(iso);
  const agora = new Date();
  const amanha = new Date(agora);
  amanha.setDate(agora.getDate() + 1);
  if (mesmoDia(iso, agora.toISOString())) return `Hoje, ${dia.charAt(0).toLowerCase()}${dia.slice(1)}`;
  if (mesmoDia(iso, amanha.toISOString())) return `Amanhã, ${dia.charAt(0).toLowerCase()}${dia.slice(1)}`;
  return dia;
}

function Numero({ valor, rotulo, rotuloAcessivel }: { valor: number; rotulo: string; rotuloAcessivel?: string }) {
  return (
    <View style={styles.numero} accessible accessibilityLabel={rotuloAcessivel ?? `${valor} ${rotulo}`}>
      <Text style={textos.numero}>{valor}</Text>
      <Text style={textos.meta}>{rotulo}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.xl, paddingBottom: espaco.xxxl },
  flex: { flex: 1 },
  cabecalho: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.sm,
    paddingBottom: espaco.lg,
  },
  saudacao: { marginTop: 2 },
  esqueletoBloco: { marginBottom: espaco.lg },
  cartaoEscuro: {
    backgroundColor: cores.tinta,
    borderRadius: raios.bloco,
    padding: espaco.xl,
    marginBottom: espaco.lg,
  },
  dataProximo: { marginTop: espaco.sm },
  linhaHora: { flexDirection: 'row', alignItems: 'baseline', gap: espaco.md, marginTop: espaco.xs },
  horaGrande: {
    fontFamily: 'InstrumentSerif_400Regular',
    fontSize: 44,
    lineHeight: 46,
    color: cores.escuroTexto,
  },
  distancia: { color: cores.escuroTextoApoio },
  nomeEscuro: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 15,
    color: cores.escuroTexto,
  },
  linhaCliente: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    marginTop: espaco.lg,
    paddingTop: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.14)',
  },
  abrirPerfil: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: espaco.sm,
    marginTop: espaco.lg,
    paddingTop: espaco.md,
    borderTopWidth: 1,
    borderTopColor: 'rgba(243, 237, 231, 0.14)',
  },
  semProximo: { marginBottom: espaco.lg },
  semProximoTexto: { marginTop: espaco.xs },
  numeros: { flexDirection: 'row', gap: espaco.sm, marginBottom: espaco.lg },
  numero: {
    flex: 1,
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.bordaSuave,
    borderRadius: raios.cartao,
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.md,
    gap: espaco.xs,
  },
  tituloSecao: { marginTop: espaco.xxl, marginBottom: espaco.md },
  tituloLinha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: espaco.md,
  },
  lista: { gap: espaco.sm },
  itemAgenda: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  horaItem: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    fontSize: 14,
    color: cores.acaoTexto,
    minWidth: 46,
  },
  pressionado: { opacity: 0.9 },
});
