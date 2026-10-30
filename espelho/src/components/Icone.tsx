import Feather from '@expo/vector-icons/Feather';

import { cores } from '@/theme/tokens';

/**
 * Ícones do app, nomeados pelo papel que cumprem.
 *
 * Substituem os glifos tipográficos do protótipo (◈ ☰ ▤ ✳ ⚿), que dependiam da fonte
 * instalada e podiam aparecer como retângulos vazios em alguns aparelhos. O mapa abaixo
 * é o único lugar que conhece a biblioteca usada.
 */
const MAPA = {
  inicio: 'home',
  clientes: 'users',
  cliente: 'user',
  agenda: 'calendar',
  perfil: 'user',
  // A simulação é representada pela câmera: a ação que o profissional executa é
  // fotografar o cliente. A tesoura ficou reservada para o que é corte de cabelo de
  // fato — o estilo escolhido e a marca do aplicativo.
  simulacao: 'camera',
  corte: 'scissors',
  camera: 'camera',
  galeria: 'image',
  imagem: 'image',
  trocarCamera: 'refresh-cw',
  cor: 'droplet',
  voltar: 'arrow-left',
  avancar: 'arrow-right',
  fechar: 'x',
  mais: 'plus',
  chevron: 'chevron-right',
  busca: 'search',
  editar: 'edit-2',
  excluir: 'trash-2',
  documento: 'file-text',
  privacidade: 'shield',
  cadeado: 'lock',
  alerta: 'alert-triangle',
  info: 'info',
  ok: 'check',
  okCirculo: 'check-circle',
  proibido: 'slash',
  relogio: 'clock',
  sino: 'bell',
  comparar: 'columns',
  vinculo: 'link-2',
  sair: 'log-out',
  ajustes: 'sliders',
  registrar: 'clipboard',
  calendario: 'calendar',
} as const;

export type NomeIcone = keyof typeof MAPA;

type Props = {
  nome: NomeIcone;
  tamanho?: number;
  cor?: string;
};

export function Icone({ nome, tamanho = 18, cor = cores.icone }: Props) {
  return <Feather name={MAPA[nome]} size={tamanho} color={cor} />;
}
