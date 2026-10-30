/**
 * Catálogo de exibição: exemplos de corte e de cor da etapa "Estilo e cor", e os serviços.
 *
 * Os exemplos são **só texto de apoio**: mostram o tipo de pedido que pode ser escrito, não
 * a lista do que é possível pedir. Foram escolhidos entre os cortes e as cores em alta em
 * 2026 e os clássicos que não saem de moda (fontes no docs/historico/RELATORIO_PERSONALIZACAO_IA.md).
 *
 * O servidor (`backend/app/services/catalogo.py`) tem os mesmos nomes: quando o texto
 * escrito é exatamente um deles, ele usa a descrição pronta em inglês e, se houver, a opção
 * equivalente do modelo principal. Um teste da suíte do servidor confere que as duas
 * listas não divergem.
 */

export const EXEMPLOS_DE_CORTE = {
  emAlta: [
    'Long bob estruturado',
    'Bob texturizado',
    'Butterfly',
    'Shaggy com franja',
    'Chanel de bico',
    'Degradê',
    'Mullet moderno',
    'Texturizado curto',
  ],
  classicos: ['Chanel', 'Pixie', 'Camadas longas', 'Franja reta', 'Corte social', 'Caesar'],
} as const;

export const EXEMPLOS_DE_COR = {
  emAlta: [
    'Loiro manteiga',
    'Loiro mel',
    'Morena iluminada',
    'Chocolate quente',
    'Cobre canela',
    'Vermelho bordô',
  ],
  classicos: ['Preto natural', 'Castanho-escuro', 'Castanho-claro', 'Loiro', 'Ruivo', 'Grisalho'],
} as const;

export const SERVICOS = ['Coloração', 'Corte', 'Hidratação', 'Escova', 'Retoque de cor'] as const;
