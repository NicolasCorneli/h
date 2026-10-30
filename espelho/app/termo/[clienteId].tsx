import { useLocalSearchParams, useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Aviso, Cartao, Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Cabecalho } from '@/components/Cabecalho';
import { DocumentoTermo } from '@/components/DocumentoTermo';
import { SeloConsentimento } from '@/components/SeloConsentimento';
import { useCliente, useResumoConsentimento } from '@/data/store';
import { rotuloFormaObtencao } from '@/services/consentService';
import { textos } from '@/theme/textos';
import { espaco } from '@/theme/tokens';
import { dataCurta, hora } from '@/utils/datas';

/**
 * Consulta do termo — somente leitura.
 *
 * Mostra o texto da versão que ESTE cliente aceitou (não necessariamente a vigente),
 * porque é esse o documento ao qual ele manifestou concordância. Nenhum elemento desta
 * tela é editável: registrar uma decisão nova é outro fluxo, em /consentimento/[id].
 */
export default function TermoSomenteLeitura() {
  const { clienteId } = useLocalSearchParams<{ clienteId: string }>();
  const router = useRouter();
  const cliente = useCliente(clienteId);
  const resumo = useResumoConsentimento(clienteId);

  // A tela mostra a versão que ESTE cliente aceitou — buscada no servidor por número de
  // versão. Sem decisão registrada, mostra a vigente, que é a que será apresentada.
  const versaoAceita = resumo.registro?.versaoTermo ?? null;
  const desatualizado = resumo.revalidar;

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

  return (
    <Tela>
      <Cabecalho
        titulo="Termo de uso de imagem"
        subtitulo={`${cliente.nome} · somente leitura`}
        aoVoltar={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.conteudo} showsVerticalScrollIndicator={false}>
        <Cartao estilo={styles.ficha}>
          <SeloConsentimento status={resumo.status} revalidar={resumo.revalidar} />
          {resumo.registro ? (
            <>
              <Text style={textos.apoio}>
                {DECISAO[resumo.registro.decisao]} em {dataCurta(resumo.registro.registradoEm)}, às{' '}
                {hora(resumo.registro.registradoEm)}
              </Text>
              <Text style={textos.apoio}>
                Confirmado por {resumo.registro.confirmadoPor} ·{' '}
                {rotuloFormaObtencao(resumo.registro.formaObtencao)}
              </Text>
              {resumo.registro.responsavel ? (
                <Text style={textos.apoio}>
                  Responsável legal: {resumo.registro.responsavel.nome} (
                  {resumo.registro.responsavel.parentesco})
                </Text>
              ) : null}
              <Text style={textos.apoio}>Versão apresentada: {resumo.registro.versaoTermo}</Text>
            </>
          ) : (
            <Text style={textos.apoio}>
              Nenhuma decisão registrada. Abaixo está a versão vigente, que será apresentada quando o
              cliente decidir.
            </Text>
          )}
        </Cartao>

        {desatualizado ? (
          <Aviso
            tom="alerta"
            titulo="Existe uma versão mais recente do termo"
            texto={`Este é o texto da versão ${versaoAceita}, que ${cliente.nome} leu. A versão vigente é a ${resumo.versaoVigente} e precisa ser apresentada antes da próxima foto.`}
          />
        ) : null}

        <DocumentoTermo tipo="cliente" versao={versaoAceita} estilo={styles.documento} />

        <Botao
          titulo={
            desatualizado ? 'Apresentar versão vigente ao cliente' : 'Registrar nova decisão do cliente'
          }
          variante="secundaria"
          icone="documento"
          aoPressionar={() => router.replace(`/consentimento/${cliente.id}`)}
          estilo={styles.acao}
        />
        <Text style={[textos.meta, styles.nota]}>
          Alterar o texto do termo não é possível pelo aplicativo: uma correção gera uma versão nova,
          que precisa ser apresentada de novo a cada cliente.
        </Text>
      </ScrollView>
    </Tela>
  );
}

const DECISAO = {
  aceito: 'Aceito',
  recusado: 'Recusado',
  revogado: 'Cancelado',
} as const;

const styles = StyleSheet.create({
  ausente: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  conteudo: { paddingHorizontal: espaco.xl, paddingTop: espaco.lg, paddingBottom: espaco.xxl },
  ficha: { gap: espaco.sm, marginBottom: espaco.md },
  documento: { marginTop: espaco.lg },
  acao: { marginTop: espaco.xl },
  nota: { marginTop: espaco.md },
});
