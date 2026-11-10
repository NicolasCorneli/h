/**
 * Teste de unidade das regras do pedido de personalização (src/utils/pedido.ts), dos
 * exemplos da tela "Estilo e cor" (src/data/catalogo.ts) e das ilustrações dos tipos de
 * cabelo (src/utils/ilustracaoTextura.ts).
 * Rodar: node --experimental-strip-types --no-warnings --import ./testes/carregar-ts.mjs testes/pedido.mjs
 */
import {
  COR_MANTIDA,
  CORTE_MANTIDO,
  GENERO_PADRAO,
  OPCOES_DE_GENERO,
  OPCOES_DE_TEXTURA,
  TEXTURA_MANTIDA,
  categoriaDaTextura,
  escolherCategoria,
  escolherTipo,
  pendencias,
  rotuloCor,
  rotuloCorte,
  rotuloGenero,
  rotuloTextura,
} from '../src/utils/pedido.ts';
import { EXEMPLOS_DE_COR, EXEMPLOS_DE_CORTE } from '../src/data/catalogo.ts';
import { LADO, mechasDaTextura } from '../src/utils/ilustracaoTextura.ts';

let falhas = 0;
let total = 0;
const conferir = (nome, obtido, esperado) => {
  total++;
  if (JSON.stringify(obtido) !== JSON.stringify(esperado)) {
    falhas++;
    console.log(`FALHA ${nome}: esperado ${JSON.stringify(esperado)}, obtido ${JSON.stringify(obtido)}`);
  }
};
const base = { corte: '', manterCorte: false, cor: '', manterCor: false };
const campos = (lista) => lista.map((p) => p.campo);

// Pendências
conferir('vazio: falta corte e cor', campos(pendencias(base)), ['corte', 'cor']);
conferir('a mensagem diz a seção e o que fazer', pendencias(base)[0].mensagem, 'Corte: descreva o corte desejado ou escolha "Manter o corte atual".');
conferir('a mensagem da cor', pendencias(base)[1].mensagem, 'Cor: descreva a cor desejada ou escolha "Manter a cor atual".');
conferir('campo vazio é do tipo vazio', pendencias(base).map((p) => p.tipo), ['vazio', 'vazio']);
conferir('só espaços conta como vazio', campos(pendencias({ ...base, corte: '   ', cor: 'Loiro' })), ['corte']);
conferir('corte e cor descritos: pronto', pendencias({ ...base, corte: 'Chanel', cor: 'Loiro' }), []);
conferir('manter o corte e mudar a cor', pendencias({ ...base, manterCorte: true, cor: 'Ruivo' }), []);
conferir('manter a cor e mudar o corte', pendencias({ ...base, corte: 'Pixie', manterCor: true }), []);
// Manter com uma descrição já escrita: não descarta em silêncio, pede uma decisão.
const conflito = pendencias({ ...base, manterCorte: true, corte: 'Chanel com franja', cor: 'Ruivo' });
conferir('manter com texto escrito é conflito', conflito.map((p) => [p.campo, p.tipo]), [['corte', 'conflito']]);
conferir('o conflito diz o que decidir', conflito[0].mensagem, 'Corte: você escreveu uma descrição, mas escolheu "Manter o corte atual". Escolha qual vale.');
conferir('conflito na cor', pendencias({ ...base, corte: 'Pixie', manterCor: true, cor: 'mechas' }).map((p) => [p.campo, p.tipo]), [['cor', 'conflito']]);
conferir('só espaços no campo mantido não é conflito', pendencias({ ...base, manterCorte: true, corte: '   ', cor: 'Ruivo' }), []);
conferir('manter os dois: nada a simular', campos(pendencias({ ...base, manterCorte: true, manterCor: true })), ['pedido']);
conferir('manter os dois e mudar o tipo de cabelo: pronto', pendencias({ ...base, manterCorte: true, manterCor: true, textura: '3B' }), []);
conferir('mensagem de nada a simular cita o tipo de cabelo', pendencias({ ...base, manterCorte: true, manterCor: true })[0].mensagem, 'Nada a simular: mude o corte, a cor ou o tipo de cabelo.');
conferir('tipo de cabelo não dispensa a descrição do corte pedido', campos(pendencias({ ...base, cor: 'Ruivo', textura: 'liso' })), ['corte']);
conferir('marcação é recusada', campos(pendencias({ ...base, corte: '<b>bob</b>', cor: 'Loiro' })), ['corte']);
conferir('chaves de modelo são recusadas', campos(pendencias({ ...base, corte: 'Chanel', cor: '{{x}}' })), ['cor']);
conferir('acentos e pontuação comum passam', pendencias({ ...base, corte: 'Degradê baixo (laterais), 2 cm!', cor: 'Loiro-mel' }), []);
conferir('números sem palavras não são descrição', campos(pendencias({ ...base, corte: '1234', cor: 'Loiro' })), ['corte']);
conferir('mais de 300 caracteres', campos(pendencias({ ...base, corte: 'a'.repeat(301), cor: 'Loiro' })), ['corte']);
conferir('exatamente 300 caracteres', pendencias({ ...base, corte: 'a'.repeat(300), cor: 'Loiro' }), []);

// Rótulos
conferir('rótulo do corte mantido', rotuloCorte({ ...base, manterCorte: true, corte: 'ignorado' }), CORTE_MANTIDO);
conferir('rótulo do corte limpa espaços', rotuloCorte({ ...base, corte: ' Chanel   de bico ' }), 'Chanel de bico');
conferir('rótulo da cor limpa espaços', rotuloCor({ ...base, cor: '  Loiro   mel ' }), 'Loiro mel');
conferir('rótulo da cor mantida', rotuloCor({ ...base, manterCor: true, cor: 'ignorado' }), COR_MANTIDA);

// Exemplos: todo exemplo mostrado na tela é um pedido aceito, e nenhum se repete.
for (const [nome, grupos] of [['corte', EXEMPLOS_DE_CORTE], ['cor', EXEMPLOS_DE_COR]]) {
  const todos = [...grupos.emAlta, ...grupos.classicos];
  conferir(`exemplos de ${nome} sem repetição`, new Set(todos.map((t) => t.toLowerCase())).size, todos.length);
  for (const exemplo of todos) {
    const pedido = nome === 'corte' ? { ...base, corte: exemplo, manterCor: true } : { ...base, cor: exemplo, manterCorte: true };
    conferir(`exemplo aceito: ${exemplo}`, pendencias(pedido), []);
  }
}
conferir('cortes: em alta e clássicos', [EXEMPLOS_DE_CORTE.emAlta.length > 0, EXEMPLOS_DE_CORTE.classicos.length > 0], [true, true]);
conferir('cores: em alta e clássicas', [EXEMPLOS_DE_COR.emAlta.length > 0, EXEMPLOS_DE_COR.classicos.length > 0], [true, true]);

// Gênero: rótulo em português na tela, valor exato do campo `gender` do modelo no envio.
conferir(
  'gênero: rótulos e valores do modelo',
  OPCOES_DE_GENERO.map((o) => [o.rotulo, o.valor]),
  [['Feminino', 'female'], ['Masculino', 'male'], ['Neutro', 'none']]
);
conferir('gênero: padrão é o do modelo (neutro)', GENERO_PADRAO, 'none');
conferir('gênero: rótulo de cada valor', ['female', 'male', 'none'].map(rotuloGenero), ['Feminino', 'Masculino', 'Neutro']);
conferir('gênero: valor desconhecido aparece como neutro', rotuloGenero('outro'), 'Neutro');
conferir('gênero não interfere nas pendências', pendencias({ ...base, corte: 'Chanel', cor: 'Loiro', genero: 'male' }), []);

// Tipo de cabelo desejado: os mesmos 16 valores do servidor (TEXTURAS em pedido.py).
const tiposEsperados = ['1A', '1B', '1C', '2A', '2B', '2C', '3A', '3B', '3C', '4A', '4B', '4C'];
conferir('categorias na ordem', OPCOES_DE_TEXTURA.map((o) => o.valor), ['liso', 'ondulado', 'cacheado', 'crespo']);
conferir('12 tipos, três por categoria', OPCOES_DE_TEXTURA.flatMap((o) => o.tipos.map((t) => t.valor)), tiposEsperados);
conferir('categoria de um tipo', ['1C', '2A', '3B', '4C', 'ondulado', null].map((t) => categoriaDaTextura(t)), ['liso', 'ondulado', 'cacheado', 'crespo', 'ondulado', null]);
conferir('rótulo de manter', rotuloTextura(null), TEXTURA_MANTIDA);
conferir('rótulo da categoria', rotuloTextura('cacheado'), 'Cacheado');
conferir('rótulo do tipo é inequívoco', rotuloTextura('2B'), 'Ondulado 2B: ondas definidas em S');

// Seleção: categoria, depois tipo; trocar de categoria troca o tipo; tocar de novo desmarca.
conferir('categoria a partir de manter', escolherCategoria(null, 'ondulado'), 'ondulado');
conferir('tipo dentro da categoria', escolherTipo('ondulado', '2B'), '2B');
conferir('tocar de novo na categoria não apaga o tipo', escolherCategoria('2B', 'ondulado'), '2B');
conferir('trocar de categoria descarta o tipo da outra', escolherCategoria('2B', 'crespo'), 'crespo');
conferir('tocar de novo no tipo volta à categoria', escolherTipo('2B', '2B'), 'ondulado');
conferir('trocar de tipo', escolherTipo('2B', '2C'), '2C');

// Ilustrações: cada tipo tem um desenho próprio, dentro do quadro.
const desenhos = [...OPCOES_DE_TEXTURA.map((o) => o.valor), ...tiposEsperados].map((t) => mechasDaTextura(t).map((m) => m.d).join('|'));
conferir('16 desenhos, todos diferentes', new Set(desenhos).size, 16);
const coordenadas = desenhos.join(' ').match(/-?\d+(\.\d+)?/g).map(Number);
conferir('todo traço cabe no quadro', coordenadas.every((v) => v >= 0 && v <= LADO), true);

console.log(falhas === 0 ? `ok: ${total} verificações do pedido` : `${falhas} de ${total} falharam`);
process.exit(falhas === 0 ? 0 : 1);
