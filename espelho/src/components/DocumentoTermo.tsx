import { useEffect } from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { useTermo } from '@/data/termos';
import type { TipoTermo } from '@/data/tipos';
import { textos } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

import { Aviso } from './Basicos';
import { Botao } from './Botao';
import { Icone } from './Icone';
import { TermoTexto } from './TermoTexto';

type Props = {
  tipo: TipoTermo;
  /** Sem versão, mostra a vigente. Com versão, mostra exatamente aquele texto. */
  versao?: string | null;
  estilo?: StyleProp<ViewStyle>;
  /**
   * Avisa a tela quando o texto está (ou não está) disponível. A tela de consentimento
   * usa isso para só liberar a decisão depois que o documento aparece: não se registra
   * aceite de um texto que o cliente não pôde ler.
   */
  aoMudarDisponibilidade?: (disponivel: boolean) => void;
};

/**
 * Bloco de documento: busca o termo no servidor e o exibe em texto somente leitura.
 *
 * Os textos deixaram de viver no pacote do aplicativo e passaram a vir da tabela
 * `termos`. Isso traz três estados que antes não existiam — carregando, falha de
 * conexão e versão desconhecida — e todos aparecem aqui, em um lugar só. Na falha, a
 * tela **não** mostra outro texto no lugar: ou é o documento certo, ou é o aviso.
 */
export function DocumentoTermo({ tipo, versao, estilo, aoMudarDisponibilidade }: Props) {
  const { termo, carregando, erro, recarregar } = useTermo(tipo, versao);

  useEffect(() => {
    aoMudarDisponibilidade?.(termo !== null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [termo !== null]);

  return (
    <View style={[styles.documento, estilo]}>
      <View style={styles.topo}>
        <Icone nome="documento" tamanho={14} cor={cores.textoApoio} />
        <Text style={textos.etiqueta}>Documento · não editável</Text>
      </View>

      {carregando ? (
        <View style={styles.espera} accessibilityLiveRegion="polite">
          <ActivityIndicator color={cores.acao} />
          <Text style={textos.apoio}>Buscando o texto do termo…</Text>
        </View>
      ) : null}

      {erro ? (
        <Aviso
          tom={erro.naoEncontrado ? 'alerta' : 'erro'}
          titulo={
            erro.naoEncontrado
              ? 'Esta versão do termo não está disponível'
              : 'Não foi possível carregar o termo'
          }
          texto={
            erro.naoEncontrado
              ? 'O texto desta versão não foi encontrado. Nenhum outro texto é mostrado no lugar, porque o cliente leu exatamente esta versão.'
              : erro.mensagem
          }>
          {erro.naoEncontrado ? null : (
            <Botao
              titulo="Tentar de novo"
              variante="texto"
              larguraTotal={false}
              aoPressionar={recarregar}
            />
          )}
        </Aviso>
      ) : null}

      {termo ? <TermoTexto termo={termo} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  documento: {
    backgroundColor: cores.superficieSuave,
    borderRadius: raios.bloco,
    padding: espaco.lg,
  },
  topo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm, marginBottom: espaco.md },
  espera: { alignItems: 'center', gap: espaco.sm, paddingVertical: espaco.xl },
});
