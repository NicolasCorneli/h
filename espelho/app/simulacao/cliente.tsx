import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Avatar, Etiqueta, Grupo, ItemGrupo, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { EstadoVazio } from '@/components/EstadoVazio';
import { Icone } from '@/components/Icone';
import { SeloConsentimento } from '@/components/SeloConsentimento';
import { useRascunho } from '@/data/rascunho';
import { useClientes, useStore } from '@/data/store';
import type { AvaliacaoCaptura } from '@/data/tipos';
import { rotaAposAvaliacao } from '@/services/consentService';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { hora, mesmoDia } from '@/utils/datas';
import { nomeCorresponde } from '@/utils/busca';

/**
 * Etapa 1 da simulação: de quem é a imagem. A câmera nunca abre antes daqui, porque
 * é o cliente quem autoriza o uso da própria imagem.
 */
export default function EscolherCliente() {
  const router = useRouter();
  const { estado } = useStore();
  const clientes = useClientes();
  const { iniciar } = useRascunho();
  const [busca, setBusca] = useState('');

  const agoraIso = new Date().toISOString();

  /** Quem tem atendimento hoje aparece primeiro: é quase sempre quem está na cadeira. */
  const deHoje = useMemo(
    () =>
      clientes.filter((c) =>
        estado.agendamentos.some(
          (a) => a.clienteId === c.id && mesmoDia(a.dataHora, agoraIso) && a.status !== 'cancelado'
        )
      ),
    [clientes, estado.agendamentos, agoraIso]
  );

  const filtrados = useMemo(() => {
    const termo = busca.trim();
    if (!termo) return clientes;
    return clientes.filter((c) => nomeCorresponde(c.nome, termo));
  }, [busca, clientes]);

  /**
   * A avaliação da captura vem do servidor, em `cliente.consentimento.bloqueio`: a tela
   * não recalcula a regra, apenas decide para onde levar.
   */
  function seguir(clienteId: string) {
    iniciar(clienteId);
    const cliente = estado.clientes.find((c) => c.id === clienteId);
    const bloqueio = cliente?.consentimento.bloqueio ?? null;
    const avaliacao: AvaliacaoCaptura = !cliente
      ? {
          permitida: false,
          motivo: 'sem_cliente',
          titulo: 'Escolha o cliente antes de fotografar',
          descricao: 'Toda simulação pertence a um cliente.',
          acao: 'escolher_cliente',
        }
      : bloqueio
        ? { permitida: false, ...bloqueio, acao: 'apresentar_termo' }
        : { permitida: true };
    router.push(rotaAposAvaliacao(avaliacao, clienteId));
  }

  const linha = (clienteId: string, detalhe?: string) => {
    const cliente = clientes.find((c) => c.id === clienteId);
    if (!cliente) return null;
    const resumo = cliente.consentimento;
    return (
      <ItemGrupo
        key={cliente.id}
        aoPressionar={() => seguir(cliente.id)}
        rotuloAcessivel={`Simular para ${cliente.nome}. ${resumo.rotulo}`}>
        <Avatar nome={cliente.nome} fotoUri={cliente.fotoUri} />
        <View style={styles.flex}>
          <Text style={textos.corpoForte}>{cliente.nome}</Text>
          {detalhe ? <Text style={textos.meta}>{detalhe}</Text> : null}
          <View style={styles.selo}>
            <SeloConsentimento status={resumo.status} revalidar={resumo.revalidar} compacto />
          </View>
        </View>
        <Icone nome="chevron" tamanho={18} />
      </ItemGrupo>
    );
  };

  if (clientes.length === 0) {
    return (
      <Tela>
        <Cabecalho titulo="Nova simulação" aoVoltar={() => router.back()} iconeVoltar="fechar" />
        <EstadoVazio
          icone="clientes"
          titulo="Nenhum cliente cadastrado"
          texto="A simulação pertence a um cliente, e é ele quem autoriza o uso da própria imagem."
          acao={{ titulo: 'Cadastrar cliente', aoPressionar: () => router.push('/cliente/editar') }}
        />
      </Tela>
    );
  }

  return (
    <Tela>
      <Cabecalho
        titulo="Para quem é a simulação?"
        subtitulo="Etapa 1 de 3"
        aoVoltar={() => router.back()}
        iconeVoltar="fechar"
      />

      <View style={styles.topo}>
        <View style={styles.busca}>
          <Icone nome="busca" tamanho={16} />
          <TextInput
            value={busca}
            onChangeText={setBusca}
            placeholder="Buscar cliente"
            placeholderTextColor={cores.placeholder}
            accessibilityLabel="Buscar cliente"
            style={styles.buscaEntrada}
          />
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.lista} showsVerticalScrollIndicator={false}>
        {busca.trim() === '' && deHoje.length > 0 ? (
          <View style={styles.bloco}>
            <Etiqueta estilo={styles.etiqueta}>Atendimentos de hoje</Etiqueta>
            <Grupo>
              {deHoje.map((c) => {
                const agendamento = estado.agendamentos.find(
                  (a) => a.clienteId === c.id && mesmoDia(a.dataHora, agoraIso) && a.status !== 'cancelado'
                );
                return linha(c.id, agendamento ? `${hora(agendamento.dataHora)} · ${agendamento.servico}` : undefined);
              })}
            </Grupo>
          </View>
        ) : null}

        <View style={styles.bloco}>
          <Etiqueta estilo={styles.etiqueta}>
            {busca.trim() ? 'Resultados' : 'Todos os clientes'}
          </Etiqueta>
          {filtrados.length === 0 ? (
            <EstadoVazio
              icone="busca"
              titulo="Nenhum resultado"
              texto={`Nenhum cliente corresponde a “${busca.trim()}”.`}
              compacto
            />
          ) : (
            <Grupo>{filtrados.map((c) => linha(c.id))}</Grupo>
          )}
        </View>

        <Text style={[textos.meta, styles.nota]}>
          Quem ainda não decidiu vê o termo na hora. Quem recusou continua com cadastro, histórico e
          agenda. Só a simulação fica indisponível.
        </Text>

        <Botao
          titulo="Cadastrar novo cliente"
          variante="texto"
          aoPressionar={() => router.push('/cliente/editar')}
          estilo={styles.novo}
        />
      </ScrollView>
    </Tela>
  );
}

const styles = StyleSheet.create({
  topo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg },
  busca: {
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.campo,
    height: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    paddingHorizontal: espaco.lg,
  },
  buscaEntrada: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_400Regular',
    fontSize: 15,
    color: cores.texto,
    paddingVertical: 0,
  },
  lista: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxxl },
  bloco: { marginBottom: espaco.xl },
  etiqueta: { marginBottom: espaco.sm },
  selo: { marginTop: espaco.xs },
  flex: { flex: 1, gap: 2 },
  nota: { marginTop: espaco.xs },
  novo: { marginTop: espaco.md },
});
