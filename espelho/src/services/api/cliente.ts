import Constants from 'expo-constants';
import { Platform } from 'react-native';

import { encerrarSessao, guardarSessao, tokenDeAcesso, tokenDeRenovacao } from './sessao';

/**
 * Cliente HTTP único do aplicativo.
 *
 * Responsabilidades: montar a URL base, enviar o token, renovar a sessão uma vez quando
 * o acesso expira, aplicar tempo limite e traduzir qualquer falha para um `ErroApi` com
 * código estável — para que as telas decidam o que mostrar sem inspecionar status HTTP.
 */

/**
 * A URL base é descoberta, nesta ordem:
 *
 * 1. `EXPO_PUBLIC_API_URL`, quando definida (produção ou configuração manual);
 * 2. no build de produção para a web, a origem do próprio site: a API fica no mesmo
 *    domínio, atrás do proxy que serve o site (`/api/...`). No build de produção para o
 *    celular não há o que adivinhar: sem a variável, a URL fica vazia e toda chamada
 *    falha dizendo isso (ver `requisitar`);
 * 3. em desenvolvimento, o endereço do próprio Metro bundler com a porta 8000, que é o que
 *    faz o aplicativo rodando no celular achar o backend no computador sem configurar IP;
 * 4. `http://localhost:8000`, usado na web em desenvolvimento.
 *
 * Antes, o build de produção sem a variável caía no passo 3 e chamava
 * `http://<domínio-do-site>:8000` na web e `http://espelho:8000` no celular.
 */
function descobrirUrlBase(): string {
  const configurada = process.env.EXPO_PUBLIC_API_URL;
  if (configurada) return configurada.replace(/\/$/, '');

  if (!__DEV__) {
    if (Platform.OS === 'web' && typeof window !== 'undefined') return window.location.origin;
    return '';
  }

  const anfitriao = Constants.expoConfig?.hostUri ?? Constants.linkingUri;
  const encontrado = anfitriao?.match(/^(?:\w+:\/\/)?([^/:]+)/);
  if (encontrado) return `http://${encontrado[1]}:8000`;

  return 'http://localhost:8000';
}

export const URL_BASE = descobrirUrlBase();
export const PREFIXO = '/api/v1';

const TEMPO_LIMITE_MS = 20_000;
const TEMPO_LIMITE_ENVIO_MS = 60_000;

export type DetalheErro = Record<string, unknown>;

export class ErroApi extends Error {
  readonly codigo: string;
  readonly status: number;
  readonly detalhes: DetalheErro[];

  constructor(mensagem: string, codigo: string, status: number, detalhes: DetalheErro[] = []) {
    super(mensagem);
    this.name = 'ErroApi';
    this.codigo = codigo;
    this.status = status;
    this.detalhes = detalhes;
  }

  /** Falhas que não vieram do servidor: aparelho sem rede, servidor desligado, demora. */
  get deConexao(): boolean {
    return this.codigo === 'sem_conexao' || this.codigo === 'tempo_esgotado';
  }
}

type Opcoes = {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  corpo?: unknown;
  formulario?: FormData;
  /** Rotas públicas (termos, catálogo, login) não precisam de token. */
  publica?: boolean;
  /** Usado internamente para não entrar em laço ao renovar a sessão. */
  semRenovar?: boolean;
  parametros?: Record<string, string | number | boolean | undefined | null>;
};

function montarUrl(caminho: string, parametros?: Opcoes['parametros']): string {
  const base = `${URL_BASE}${PREFIXO}${caminho}`;
  if (!parametros) return base;
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== null && valor !== '') busca.append(chave, String(valor));
  }
  const consulta = busca.toString();
  return consulta ? `${base}?${consulta}` : base;
}

async function lerErro(resposta: Response): Promise<ErroApi> {
  let codigo = `http_${resposta.status}`;
  let mensagem = 'Não foi possível concluir a ação.';
  let detalhes: DetalheErro[] = [];
  try {
    const corpo = await resposta.json();
    const erro = corpo?.erro;
    if (erro) {
      codigo = erro.codigo ?? codigo;
      mensagem = erro.mensagem ?? mensagem;
      detalhes = Array.isArray(erro.detalhes) ? erro.detalhes : [];
    }
  } catch {
    // Resposta sem JSON (por exemplo, um proxy no caminho): fica a mensagem genérica.
  }
  return new ErroApi(mensagem, codigo, resposta.status, detalhes);
}

/**
 * Resultado da renovação. `sem_conexao` é diferente de `recusada`: o aparelho não falou
 * com o servidor, e a sessão pode muito bem continuar válida. Tratar os dois como iguais
 * desconectava o profissional por causa de um túnel ou de um Wi-Fi instável.
 */
type Renovacao = 'renovada' | 'recusada' | 'sem_conexao';

let renovacaoEmAndamento: Promise<Renovacao> | null = null;

/** Troca o refresh por um acesso novo. Uma renovação por vez, compartilhada. */
async function renovarSessao(): Promise<Renovacao> {
  const renovacao = tokenDeRenovacao();
  if (!renovacao) {
    await encerrarSessao();
    return 'recusada';
  }

  renovacaoEmAndamento ??= (async (): Promise<Renovacao> => {
    const controle = new AbortController();
    const limite = setTimeout(() => controle.abort(), TEMPO_LIMITE_MS);
    try {
      const resposta = await fetch(montarUrl('/auth/renovar'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken: renovacao }),
        signal: controle.signal,
      });
      // Só uma recusa do próprio servidor (4xx) encerra a sessão. Um 5xx ou um proxy
      // fora do ar não diz nada sobre o token.
      if (resposta.status >= 400 && resposta.status < 500) {
        await encerrarSessao();
        return 'recusada';
      }
      if (!resposta.ok) return 'sem_conexao';
      const tokens = await resposta.json();
      await guardarSessao(tokens.accessToken, tokens.refreshToken ?? renovacao);
      return 'renovada';
    } catch {
      return 'sem_conexao';
    } finally {
      clearTimeout(limite);
      renovacaoEmAndamento = null;
    }
  })();

  return renovacaoEmAndamento;
}

export async function requisitar<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const { metodo = 'GET', corpo, formulario, publica, semRenovar, parametros } = opcoes;

  if (!URL_BASE) {
    // Build do celular gerado sem EXPO_PUBLIC_API_URL: é erro de publicação, não de rede.
    throw new ErroApi(
      'Este aplicativo foi gerado sem o endereço do servidor. Avise o suporte.',
      'servidor_nao_configurado',
      0
    );
  }

  const cabecalhos: Record<string, string> = {};
  if (!publica) {
    const token = tokenDeAcesso();
    if (token) cabecalhos.Authorization = `Bearer ${token}`;
  }
  if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json';

  const controle = new AbortController();
  const limite = setTimeout(
    () => controle.abort(),
    formulario ? TEMPO_LIMITE_ENVIO_MS : TEMPO_LIMITE_MS
  );

  let resposta: Response;
  try {
    resposta = await fetch(montarUrl(caminho, parametros), {
      method: metodo,
      headers: cabecalhos,
      body: formulario ?? (corpo !== undefined ? JSON.stringify(corpo) : undefined),
      signal: controle.signal,
    });
  } catch (erro) {
    const abortado = erro instanceof Error && erro.name === 'AbortError';
    // Em desenvolvimento, a causa real vai para o terminal do Expo: "sem conexão" na tela
    // pode ser rede, endereço errado ou o servidor fechando a conexão durante um envio.
    if (__DEV__) console.warn(`[api] ${metodo} ${caminho} falhou antes da resposta:`, erro);
    throw new ErroApi(
      abortado
        ? 'O sistema demorou demais para responder. Tente de novo.'
        : 'Sem conexão. Verifique a internet e tente de novo.',
      abortado ? 'tempo_esgotado' : 'sem_conexao',
      0
    );
  } finally {
    clearTimeout(limite);
  }

  if (resposta.status === 401 && !publica && !semRenovar) {
    const renovacao = await renovarSessao();
    if (renovacao === 'renovada') {
      return requisitar<T>(caminho, { ...opcoes, semRenovar: true });
    }
    if (renovacao === 'sem_conexao') {
      // A sessão fica guardada: na próxima tentativa, com rede, a renovação acontece.
      throw new ErroApi(
        'Sem conexão. Verifique a internet e tente de novo.',
        'sem_conexao',
        0
      );
    }
    // Recusada: `renovarSessao` já encerrou a sessão e a interface volta para o login.
  }

  if (!resposta.ok) throw await lerErro(resposta);
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

export const api = {
  obter: <T>(caminho: string, parametros?: Opcoes['parametros'], publica = false) =>
    requisitar<T>(caminho, { parametros, publica }),
  criar: <T>(caminho: string, corpo?: unknown, publica = false) =>
    requisitar<T>(caminho, { metodo: 'POST', corpo, publica }),
  atualizar: <T>(caminho: string, corpo?: unknown) =>
    requisitar<T>(caminho, { metodo: 'PATCH', corpo }),
  excluir: <T = void>(caminho: string, corpo?: unknown) =>
    requisitar<T>(caminho, { metodo: 'DELETE', corpo }),
  enviar: <T>(caminho: string, formulario: FormData) =>
    requisitar<T>(caminho, { metodo: 'POST', formulario }),
};
