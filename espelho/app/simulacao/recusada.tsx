import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BotaoIcone } from '@/components/Basicos';
import { Botao } from '@/components/Botao';
import { Icone } from '@/components/Icone';
import { useRascunho } from '@/data/rascunho';
import { useStore } from '@/data/store';
import { textosEscuros } from '@/theme/textos';
import { cores, espaco, raios } from '@/theme/tokens';

/** Recusa local da foto: nenhuma chamada de IA é gasta (seções 4.2 e 5.8 do pré-projeto). */
export default function FotoRecusada() {
  const router = useRouter();
  const { rascunho, atualizar } = useRascunho();
  const { estado } = useStore();
  const cliente = estado.clientes.find((c) => c.id === rascunho.clienteId);

  return (
    <SafeAreaView style={styles.tela} edges={['top', 'bottom']}>
      <View style={styles.topo}>
        <BotaoIcone icone="fechar" aoPressionar={() => router.dismissAll()} rotuloAcessivel="Fechar" escuro />
        <Text style={styles.nomeCliente}>{cliente?.nome ?? 'Sem cliente vinculado'}</Text>
        <View style={styles.espaco} />
      </View>

      <View style={styles.visor}>
        <View style={styles.guia} />
      </View>

      <View style={styles.rodape}>
        <View style={styles.caixa}>
          <View style={styles.caixaTopo}>
            <View style={styles.icone}>
              <Icone nome="alerta" tamanho={18} cor="#FFFFFF" />
            </View>
            <Text style={[textosEscuros.secao, styles.flex]}>Foto recusada antes do envio</Text>
          </View>

          <Text style={[textosEscuros.corpo, styles.subtitulo]}>
            Nenhum crédito de simulação foi usado.{' '}
            {rascunho.problemas.length > 1
              ? 'Dois pontos impedem um resultado confiável:'
              : 'Um ponto impede um resultado confiável:'}
          </Text>

          <View style={styles.motivos}>
            {rascunho.problemas.map((p) => (
              <View key={p.titulo} style={styles.motivo}>
                <View style={styles.bolinha} />
                <Text style={styles.motivoTexto}>
                  <Text style={styles.motivoTitulo}>{p.titulo}:</Text> {p.detalhe}
                </Text>
              </View>
            ))}
          </View>

          <Botao
            titulo="Tentar novamente"
            variante="secundaria"
            icone="camera"
            aoPressionar={() => {
              atualizar({ problemas: [] });
              router.back();
            }}
            estilo={styles.botao}
          />
          <Botao
            titulo="Usar esta foto assim mesmo"
            variante="texto"
            aoPressionar={() => {
              atualizar({ problemas: [] });
              router.replace('/simulacao/parametros');
            }}
            rotuloAcessivel="Usar esta foto assim mesmo, ciente de que o resultado pode ficar inconsistente"
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cores.camera },
  topo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: espaco.xl,
    paddingTop: espaco.sm,
  },
  nomeCliente: { fontFamily: 'FamiljenGrotesk_600SemiBold', fontSize: 15, color: cores.escuroTexto },
  espaco: { width: 44 },
  flex: { flex: 1 },
  visor: {
    flex: 1,
    marginVertical: espaco.lg,
    backgroundColor: '#15110F',
    alignItems: 'center',
    justifyContent: 'center',
  },
  guia: {
    width: 220,
    height: 296,
    borderRadius: 140,
    borderWidth: 2,
    borderColor: 'rgba(190,74,58,0.9)',
  },
  rodape: { paddingHorizontal: espaco.xl, paddingBottom: espaco.md },
  caixa: {
    backgroundColor: '#241B18',
    borderWidth: 1,
    borderColor: 'rgba(190,74,58,0.5)',
    borderRadius: raios.cartao,
    padding: espaco.xl,
  },
  caixaTopo: { flexDirection: 'row', alignItems: 'center', gap: espaco.md, marginBottom: espaco.md },
  icone: {
    width: 32,
    height: 32,
    borderRadius: raios.campo,
    backgroundColor: cores.erro,
    alignItems: 'center',
    justifyContent: 'center',
  },
  subtitulo: { marginBottom: espaco.md },
  motivos: { gap: espaco.sm, marginBottom: espaco.xl },
  motivo: { flexDirection: 'row', gap: espaco.md, alignItems: 'flex-start' },
  bolinha: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#D9705C',
    marginTop: 7,
  },
  motivoTexto: {
    flex: 1,
    fontFamily: 'FamiljenGrotesk_400Regular',
    fontSize: 14,
    lineHeight: 20,
    color: cores.escuroTextoSecundario,
  },
  motivoTitulo: { fontFamily: 'FamiljenGrotesk_600SemiBold' },
  botao: { marginBottom: espaco.xs },
});
