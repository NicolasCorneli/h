// Lint do aplicativo: a configuração do Expo (regras de React, hooks e importações).
// Rodar: `npm run lint`. Falha com erro; avisos não bloqueiam.
const { defineConfig, globalIgnores } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  // Saídas de build e as baterias de navegador (scripts Node com Playwright, fora do app).
  globalIgnores(['dist/*', 'web-build/*', '.expo/*', 'e2e/*', 'testes/*']),
  expoConfig,
  {
    rules: {
      // As duas regras miram o React Compiler, que este projeto não habilita. Elas apontam
      // padrões comuns do React Native que funcionam corretamente sem ele:
      // `useRef(new Animated.Value(0)).current` nas animações e o estado sincronizado com
      // um parâmetro de rota num efeito. Ficam como aviso, para revisão ao ligar o
      // compilador, em vez de bloquear.
      'react-hooks/refs': 'warn',
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
]);
