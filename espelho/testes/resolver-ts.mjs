/**
 * Gancho de resolução para os testes de unidade: o código do aplicativo importa
 * `./duracao` sem extensão (é o que o Metro e o TypeScript esperam), e o Node exige a
 * extensão. Aqui, quando a importação relativa sem extensão falha, tenta-se com `.ts`.
 * Uso: node --experimental-strip-types --import ./testes/carregar-ts.mjs testes/<teste>.mjs
 */
export async function resolve(especificador, contexto, proximo) {
  try {
    return await proximo(especificador, contexto);
  } catch (erro) {
    if (especificador.startsWith('.') && !/\.[cm]?[jt]sx?$/.test(especificador)) {
      return proximo(`${especificador}.ts`, contexto);
    }
    throw erro;
  }
}
