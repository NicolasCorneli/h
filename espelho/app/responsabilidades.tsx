import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Tela } from '@/components/Basicos';
import { Cabecalho } from '@/components/Cabecalho';
import { Botao } from '@/components/Botao';
import { DocumentoTermo } from '@/components/DocumentoTermo';
import { useFeedback } from '@/components/Feedback';
import { Icone } from '@/components/Icone';
import { useStore } from '@/data/store';
import { ErroApi } from '@/services/api';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';
import { dataCurta, hora } from '@/utils/datas';

/**
 * Ciência das responsabilidades do profissional — obrigatória no primeiro acesso.
 *
 * Não é o consentimento de imagem: aquele pertence ao cliente e é registrado no perfil
 * dele. Aqui o profissional reconhece que precisa informar o cliente antes de registrar
 * qualquer decisão, inclusive sobre o envio da foto a uma empresa terceira.
 */
export default function Responsabilidades() {
  const router = useRouter();
  const { estado, acoes } = useStore();
  const { avisar } = useFeedback();
  const [ciente, setCiente] = useState(false);
  const [documentoPronto, setDocumentoPronto] = useState(false);
  const [registrando, setRegistrando] = useState(false);

  const ciencia = estado.cienciaProfissional;
  const jaAceita = ciencia.aceita;

  return (
    <Tela>
      {/* Sem ciência registrada não há para onde voltar: o aplicativo só abre depois dela. */}
      <Cabecalho titulo="Termos e responsabilidades" aoVoltar={jaAceita ? () => router.back() : undefined} />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        {jaAceita && ciencia.registradaEm ? (
          <Aviso
            tom="sucesso"
            titulo="Ciência registrada"
            texto={`Aceita em ${dataCurta(ciencia.registradaEm)}, às ${hora(
              ciencia.registradaEm
            )}, na versão ${ciencia.versao}.`}
          />
        ) : null}

        <DocumentoTermo
          tipo="profissional"
          estilo={jaAceita ? styles.comEspaco : undefined}
          aoMudarDisponibilidade={setDocumentoPronto}
        />

        {!jaAceita ? (
          <Pressable
            onPress={() => setCiente((v) => !v)}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: ciente }}
            accessibilityLabel="Estou ciente de que devo informar o cliente antes de registrar a decisão dele"
            style={styles.caixaCiencia}>
            <View style={[styles.marcador, ciente && styles.marcadorAtivo]}>
              {ciente ? <Icone nome="ok" tamanho={14} cor="#FFFFFF" /> : null}
            </View>
            <Text style={[textos.apoio, styles.cienciaTexto]}>
              Estou ciente de que devo apresentar o termo e explicar o envio da foto a uma empresa terceira
              antes de registrar a decisão de cada cliente.
            </Text>
          </Pressable>
        ) : null}
      </ScrollView>

      {!jaAceita ? (
        <View style={styles.rodape}>
          <Botao
            titulo={registrando ? 'Registrando…' : 'Entendi, continuar'}
            carregando={registrando}
            desabilitado={!ciente || !documentoPronto}
            dicaAcessivel={
              !documentoPronto
                ? 'Aguarde o texto do aviso carregar'
                : !ciente
                  ? 'Marque a caixa de ciência para continuar'
                  : undefined
            }
            aoPressionar={async () => {
              setRegistrando(true);
              try {
                await acoes.aceitarCiencia();
                router.replace('/(tabs)');
              } catch (falha) {
                const apiErro = falha instanceof ErroApi ? falha : null;
                avisar(apiErro?.message ?? 'Não foi possível registrar agora', 'erro');
              } finally {
                setRegistrando(false);
              }
            }}
          />
          <Text style={[textos.meta, styles.nota]}>
            O consentimento de uso de imagem é registrado no perfil de cada cliente, não aqui.
          </Text>
        </View>
      ) : null}
    </Tela>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxl },
  comEspaco: { marginTop: espaco.lg },
  caixaCiencia: {
    marginTop: espaco.lg,
    flexDirection: 'row',
    gap: espaco.md,
    alignItems: 'flex-start',
    backgroundColor: cores.superficie,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: raios.cartao,
    padding: espaco.lg,
  },
  marcador: {
    width: 24,
    height: 24,
    borderRadius: 7,
    borderWidth: 1.5,
    borderColor: cores.bordaForte,
    backgroundColor: cores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
  },
  marcadorAtivo: { borderColor: cores.sucesso, backgroundColor: cores.sucesso },
  cienciaTexto: { flex: 1, color: cores.textoSecundario },
  rodape: {
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.md,
    paddingBottom: espaco.lg,
    borderTopWidth: 1,
    borderTopColor: cores.bordaSuave,
  },
  nota: { textAlign: 'center', marginTop: espaco.md },
});
