import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { AvisoDeConexao, useFalhouAoCarregar } from '@/components/AvisoDeConexao';
import { Avatar, Esqueleto, Faixa, Grupo, ItemGrupo, Tela } from '@/components/Basicos';
import { EstadoVazio } from '@/components/EstadoVazio';
import { Icone } from '@/components/Icone';
import { SeloConsentimento } from '@/components/SeloConsentimento';
import { useClientes, useStore } from '@/data/store';
import { useAtualizar } from '@/components/Atualizar';
import { textos, textosEscuros } from '@/theme/textos';
import { ALVO_TOQUE, cores, espaco, raios } from '@/theme/tokens';
import { diaMesCurto, hora, mesmoDia } from '@/utils/datas';
import { nomeCorresponde } from '@/utils/busca';

/** T3 — lista de clientes: busca no topo, estado do consentimento visível em cada linha. */
export default function Clientes() {
  const router = useRouter();
  const { controle } = useAtualizar();
  const { estado, carregando } = useStore();
  const clientes = useClientes();
  const [busca, setBusca] = useState('');

  const filtrados = useMemo(() => {
    const termo = busca.trim();
    if (!termo) return clientes;
    const digitos = termo.replace(/\D/g, '');
    return clientes.filter(
      (c) =>
        nomeCorresponde(c.nome, termo) ||
        (digitos.length > 0 && c.telefone.replace(/\D/g, '').includes(digitos))
    );
  }, [busca, clientes]);

  const descricaoDoUltimo = (clienteId: string) => {
    const agoraIso = new Date().toISOString();
    const agendadoHoje = estado.agendamentos.find(
      (a) => a.clienteId === clienteId && mesmoDia(a.dataHora, agoraIso) && a.status !== 'cancelado'
    );
    if (agendadoHoje) return `Hoje às ${hora(agendadoHoje.dataHora)}`;

    const ultimo = estado.historico
      .filter((h) => h.clienteId === clienteId)
      .sort((a, b) => b.dataServico.localeCompare(a.dataServico))[0];
    return ultimo ? `Último atendimento em ${diaMesCurto(ultimo.dataServico)}` : 'Sem atendimentos ainda';
  };

  const falhou = useFalhouAoCarregar();
  // Sem dados *e* sem falha é lista vazia de verdade. Com falha, não se sabe — e afirmar
  // que não há clientes seria dizer ao profissional que eles desapareceram.
  const vazio = clientes.length === 0 && !falhou;

  return (
    <Tela>
      <Faixa estilo={styles.topo}>
        <View style={styles.tituloLinha}>
          <Text style={textosEscuros.titulo} accessibilityRole="header">
            Clientes
          </Text>
          {!vazio ? (
            <Pressable
              onPress={() => router.push('/cliente/editar')}
              accessibilityRole="button"
              accessibilityLabel="Cadastrar cliente"
              style={({ pressed }) => [styles.botaoMais, pressed && styles.pressionado]}>
              <Icone nome="mais" tamanho={20} cor="#FFFFFF" />
            </Pressable>
          ) : null}
        </View>

        {!vazio ? (
          <View style={styles.busca}>
            <Icone nome="busca" tamanho={16} />
            <TextInput
              value={busca}
              onChangeText={setBusca}
              placeholder="Buscar por nome ou telefone"
              placeholderTextColor={cores.placeholder}
              accessibilityLabel="Buscar cliente por nome ou telefone"
              style={styles.buscaEntrada}
            />
            {busca.length > 0 ? (
              <Pressable
                onPress={() => setBusca('')}
                accessibilityRole="button"
                accessibilityLabel="Limpar busca"
                hitSlop={12}>
                <Icone nome="fechar" tamanho={16} />
              </Pressable>
            ) : null}
          </View>
        ) : null}
      </Faixa>

      <AvisoDeConexao />

      {carregando ? (
        <View style={styles.lista}>
          <Esqueleto altura={64} estilo={styles.esqueleto} />
          <Esqueleto altura={64} estilo={styles.esqueleto} />
          <Esqueleto altura={64} estilo={styles.esqueleto} />
        </View>
      ) : falhou &&
        clientes.length ===
          0 ? // A faixa de aviso acima já explicou o que aconteceu. Repetir em um estado vazio
      // ("Nenhum resultado") diria algo que não se sabe.
      null : vazio ? (
        <EstadoVazio
          icone="clientes"
          titulo="Nenhum cliente cadastrado"
          texto="Cada simulação pertence a um cliente: é ele quem autoriza o uso da própria imagem."
          acao={{ titulo: 'Cadastrar cliente', aoPressionar: () => router.push('/cliente/editar') }}
        />
      ) : (
        <ScrollView
          contentContainerStyle={styles.lista}
          showsVerticalScrollIndicator={false}
          refreshControl={controle}>
          {/* A etiqueta é toda em maiúsculas; aqui o "a" do meio fica minúsculo de
              propósito ("DE A a Z"), por isso o texto já vem em caixa e sem a conversão. */}
          <Text
            style={[textos.etiqueta, styles.semCaixaAlta, styles.contagem]}
            accessibilityLabel={`${filtrados.length} ${filtrados.length === 1 ? 'cliente' : 'clientes'}, em ordem alfabética`}>
            {`${filtrados.length} ${filtrados.length === 1 ? 'CLIENTE' : 'CLIENTES'} · DE A a Z`}
          </Text>

          {filtrados.length === 0 ? (
            <EstadoVazio
              icone="busca"
              titulo="Nenhum resultado"
              texto={`Nenhum cliente corresponde a “${busca.trim()}”. Confira a grafia ou cadastre um novo.`}
              acao={{ titulo: 'Cadastrar cliente', aoPressionar: () => router.push('/cliente/editar') }}
              compacto
            />
          ) : (
            <Grupo>
              {filtrados.map((c) => {
                const consentimento = c.consentimento;
                return (
                  <ItemGrupo
                    key={c.id}
                    aoPressionar={() => router.push(`/cliente/${c.id}`)}
                    rotuloAcessivel={`${c.nome}. ${consentimento.rotulo}. ${descricaoDoUltimo(c.id)}`}>
                    <Avatar nome={c.nome} fotoUri={c.fotoUri} />
                    <View style={styles.flex}>
                      <Text style={textos.corpoForte}>{c.nome}</Text>
                      <Text style={textos.meta}>{descricaoDoUltimo(c.id)}</Text>
                      <View style={styles.selos}>
                        <SeloConsentimento
                          status={consentimento.status}
                          revalidar={consentimento.revalidar}
                          compacto
                        />
                      </View>
                    </View>
                    <Icone nome="chevron" tamanho={18} />
                  </ItemGrupo>
                );
              })}
            </Grupo>
          )}
        </ScrollView>
      )}
    </Tela>
  );
}

const styles = StyleSheet.create({
  topo: { paddingHorizontal: espaco.xl, paddingTop: espaco.sm, paddingBottom: espaco.md },
  tituloLinha: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: espaco.md,
  },
  botaoMais: {
    width: ALVO_TOQUE,
    height: ALVO_TOQUE,
    borderRadius: raios.campo,
    backgroundColor: cores.acao,
    alignItems: 'center',
    justifyContent: 'center',
  },
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
    // `alignSelf: stretch` é o que faz o campo ocupar a altura inteira da linha. Sem
    // isso ele mede 18px dentro de uma linha de 48px: a linha *parece* clicável, mas só
    // a faixa central foca o campo — abaixo do alvo de 44px que o projeto adota.
    alignSelf: 'stretch',
    fontFamily: 'FamiljenGrotesk_400Regular',
    fontSize: 15,
    color: cores.texto,
    paddingVertical: 0,
  },
  lista: { paddingHorizontal: espaco.xl, paddingBottom: espaco.xxl, gap: espaco.sm },
  semCaixaAlta: { textTransform: 'none' },
  contagem: { paddingVertical: espaco.md, paddingHorizontal: espaco.xs },
  esqueleto: { borderRadius: raios.cartao },
  flex: { flex: 1, gap: 2 },
  selos: { flexDirection: 'row', gap: espaco.sm, marginTop: espaco.sm, flexWrap: 'wrap' },
  pressionado: { opacity: 0.85 },
});
