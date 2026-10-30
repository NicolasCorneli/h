import { useRouter } from 'expo-router';
import { Tabs, type BottomTabBarProps } from 'expo-router/js-tabs';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icone, type NomeIcone } from '@/components/Icone';
import { ALVO_TOQUE, cores, elevacao, espaco, raios } from '@/theme/tokens';

const ABAS: { nome: string; rotulo: string; icone: NomeIcone }[] = [
  { nome: 'index', rotulo: 'Início', icone: 'inicio' },
  { nome: 'clientes', rotulo: 'Clientes', icone: 'clientes' },
  { nome: 'agenda', rotulo: 'Agenda', icone: 'agenda' },
  { nome: 'perfil', rotulo: 'Perfil', icone: 'perfil' },
];

export default function LayoutAbas() {
  return (
    <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <BarraAbas {...props} />}>
      <Tabs.Screen name="index" />
      <Tabs.Screen name="clientes" />
      <Tabs.Screen name="agenda" />
      <Tabs.Screen name="perfil" />
    </Tabs>
  );
}

/**
 * Barra própria porque a ação de simular é um botão flutuante no centro: ele navega
 * para a escolha do cliente, não seleciona uma aba.
 */
function BarraAbas({ state, navigation }: BottomTabBarProps) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const rotaAtual = state.routes[state.index]?.name;

  const irPara = (nome: string) => {
    const evento = navigation.emit({ type: 'tabPress', target: nome, canPreventDefault: true });
    if (!evento.defaultPrevented) navigation.navigate(nome);
  };

  const aba = (item: (typeof ABAS)[number]) => {
    const ativo = rotaAtual === item.nome;
    return (
      <Pressable
        key={item.nome}
        onPress={() => irPara(item.nome)}
        accessibilityRole="tab"
        accessibilityState={{ selected: ativo }}
        accessibilityLabel={item.rotulo}
        style={styles.aba}>
        <Icone nome={item.icone} tamanho={20} cor={ativo ? cores.escuroTexto : cores.escuroTextoApoio} />
        <Text style={[styles.rotulo, ativo && styles.rotuloAtivo]}>{item.rotulo}</Text>
        {/* Marca da aba ativa: a cor não é o único sinal (WCAG 1.4.1). */}
        <View style={[styles.marcaAtiva, ativo && styles.marcaAtivaVisivel]} />
      </Pressable>
    );
  };

  return (
    <View style={[styles.barra, { paddingBottom: Math.max(insets.bottom, espaco.md) }]}>
      <View style={styles.conteudo}>
        {ABAS.slice(0, 2).map(aba)}
        <View style={styles.centro}>
          <Pressable
            onPress={() => router.push('/simulacao/cliente')}
            accessibilityRole="button"
            accessibilityLabel="Nova simulação"
            style={({ pressed }) => [styles.botaoCentral, elevacao.flutuante, pressed && styles.pressionado]}>
            <Icone nome="simulacao" tamanho={22} cor="#FFFFFF" />
          </Pressable>
        </View>
        {ABAS.slice(2).map(aba)}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  barra: {
    backgroundColor: cores.base,
    borderTopWidth: 1,
    borderTopColor: cores.baseBorda,
    paddingTop: espaco.sm,
    paddingHorizontal: espaco.sm,
  },
  conteudo: {
    flexDirection: 'row',
    // Abas e botão central centralizados na mesma linha. Antes os itens alinhavam pelo
    // topo e o botão subia com uma margem negativa fixa, saindo da barra.
    alignItems: 'center',
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  aba: {
    flex: 1,
    alignItems: 'center',
    gap: espaco.xs,
    minHeight: ALVO_TOQUE,
    paddingTop: espaco.xs,
  },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  botaoCentral: {
    width: 54,
    height: 54,
    borderRadius: raios.cartao,
    backgroundColor: cores.acao,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rotulo: {
    fontFamily: 'FamiljenGrotesk_500Medium',
    fontSize: 11,
    color: cores.escuroTextoApoio,
  },
  rotuloAtivo: {
    fontFamily: 'FamiljenGrotesk_600SemiBold',
    color: cores.escuroTexto,
  },
  marcaAtiva: { width: 16, height: 2, borderRadius: 1, backgroundColor: 'transparent' },
  marcaAtivaVisivel: { backgroundColor: cores.acaoDecorativa },
  pressionado: { opacity: 0.85 },
});
