import { Redirect } from 'expo-router';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Tela } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { useStore } from '@/data/store';
import { textos } from '@/theme/textos';
import { cores, espaco } from '@/theme/tokens';

/**
 * Porta de entrada: sem sessão vai ao onboarding; com sessão, a ciência das
 * responsabilidades precisa estar aceita antes de o app abrir.
 *
 * Aqui também aparece a espera da primeira carga e a falha de conexão — antes o estado
 * vinha do próprio aparelho e não havia o que esperar nem o que falhar.
 */
export default function Entrada() {
  const { estado, acoes, carregando, erroDeCarga } = useStore();

  if (carregando) {
    return (
      <Tela>
        <View style={styles.centro}>
          <ActivityIndicator color={cores.acao} />
          <Text style={[textos.apoio, styles.texto]}>Carregando seus dados…</Text>
        </View>
      </Tela>
    );
  }

  if (erroDeCarga) {
    return (
      <Tela>
        <View style={styles.centro}>
          <Text style={textos.titulo} accessibilityRole="header">
            Sem conexão
          </Text>
          <Text style={[textos.apoio, styles.texto]}>{erroDeCarga}</Text>
          <Botao
            titulo="Tentar de novo"
            larguraTotal={false}
            aoPressionar={() => void acoes.recarregar()}
            estilo={styles.botao}
          />
          <Botao
            titulo="Sair da conta"
            variante="texto"
            larguraTotal={false}
            aoPressionar={() => void acoes.sair()}
          />
        </View>
      </Tela>
    );
  }

  if (!estado.autenticado) return <Redirect href="/onboarding" />;
  if (!estado.cienciaProfissional.aceita) return <Redirect href="/responsabilidades" />;
  return <Redirect href="/(tabs)" />;
}

const styles = StyleSheet.create({
  centro: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.xxl,
    gap: espaco.sm,
  },
  texto: { textAlign: 'center' },
  // O Botao estreito se alinha à esquerda por padrão; aqui, como o texto, fica no centro.
  botao: { marginTop: espaco.lg, alignSelf: 'center' },
});
