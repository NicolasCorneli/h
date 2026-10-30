import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

/**
 * Guarda da sessão: tokens de acesso e renovação.
 *
 * No aparelho os tokens ficam no armazenamento seguro do sistema (Keychain no iOS,
 * Keystore no Android). Na web o SecureStore não existe, e aí cai para o AsyncStorage —
 * com a ressalva, registrada na documentação, de que a versão web é a de demonstração.
 *
 * Vive fora do React porque o cliente HTTP precisa do token em qualquer chamada,
 * inclusive nas que não partem de um componente.
 */

const CHAVE_ACESSO = 'espelho.token.acesso';
const CHAVE_RENOVACAO = 'espelho.token.renovacao';

type Tokens = { acesso: string; renovacao: string };

let emMemoria: Tokens | null = null;
let seguroDisponivel: boolean | null = null;

async function temArmazenamentoSeguro(): Promise<boolean> {
  if (seguroDisponivel === null) {
    try {
      seguroDisponivel = await SecureStore.isAvailableAsync();
    } catch {
      seguroDisponivel = false;
    }
  }
  return seguroDisponivel;
}

async function gravar(chave: string, valor: string): Promise<void> {
  if (await temArmazenamentoSeguro()) {
    await SecureStore.setItemAsync(chave, valor);
    return;
  }
  await AsyncStorage.setItem(chave, valor);
}

async function ler(chave: string): Promise<string | null> {
  if (await temArmazenamentoSeguro()) {
    return SecureStore.getItemAsync(chave);
  }
  return AsyncStorage.getItem(chave);
}

async function apagar(chave: string): Promise<void> {
  if (await temArmazenamentoSeguro()) {
    await SecureStore.deleteItemAsync(chave);
    return;
  }
  await AsyncStorage.removeItem(chave);
}

/** Lê os tokens guardados no aparelho. Chamado uma vez, na abertura do aplicativo. */
export async function restaurarSessao(): Promise<Tokens | null> {
  try {
    const [acesso, renovacao] = await Promise.all([ler(CHAVE_ACESSO), ler(CHAVE_RENOVACAO)]);
    emMemoria = acesso && renovacao ? { acesso, renovacao } : null;
  } catch {
    emMemoria = null;
  }
  return emMemoria;
}

export async function guardarSessao(acesso: string, renovacao: string): Promise<void> {
  emMemoria = { acesso, renovacao };
  try {
    await Promise.all([gravar(CHAVE_ACESSO, acesso), gravar(CHAVE_RENOVACAO, renovacao)]);
  } catch {
    // Se o armazenamento falhar, a sessão continua válida nesta execução.
  }
}

type Ouvinte = () => void;
const ouvintes = new Set<Ouvinte>();

/**
 * Avisa quando a sessão acaba, venha o fim de onde vier: o botão "Sair", a exclusão da
 * conta ou o servidor recusando a renovação no meio do uso. Sem isso o cliente HTTP
 * apagava os tokens e a interface continuava como se houvesse alguém conectado, mostrando
 * erros em todas as telas em vez de voltar para o login.
 */
export function aoEncerrarSessao(ouvinte: Ouvinte): () => void {
  ouvintes.add(ouvinte);
  return () => {
    ouvintes.delete(ouvinte);
  };
}

export async function encerrarSessao(): Promise<void> {
  const havia = emMemoria !== null;
  emMemoria = null;
  if (havia) ouvintes.forEach((ouvinte) => ouvinte());
  try {
    await Promise.all([apagar(CHAVE_ACESSO), apagar(CHAVE_RENOVACAO)]);
  } catch {
    // Nada a fazer: o importante é que a memória já foi limpa.
  }
}

export function tokenDeAcesso(): string | null {
  return emMemoria?.acesso ?? null;
}

export function tokenDeRenovacao(): string | null {
  return emMemoria?.renovacao ?? null;
}

export function temSessao(): boolean {
  return emMemoria !== null;
}
