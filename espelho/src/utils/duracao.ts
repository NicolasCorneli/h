/**
 * Duração digitada pelo profissional, em texto livre, convertida para minutos.
 *
 * Aceita o jeito como se fala no salão: "45", "45 min", "45 minutos", "1h", "1 hora",
 * "2 horas", "1h30", "1h 30min", "1 hora e 30 minutos", "1:30" e "1,5h". Número sozinho
 * é minuto. A faixa é a mesma do servidor (`DURACAO_MINIMA` e `DURACAO_MAXIMA` em
 * `backend/app/schemas/base.py`) e da restrição no banco.
 */

export const DURACAO_MINIMA = 15;
export const DURACAO_MAXIMA = 480;

export const EXEMPLO_DURACAO = 'Por exemplo: 45 min, 1h ou 1h30';

export type LeituraDuracao =
  /** Campo vazio: duração não informada (é opcional). */
  | { tipo: 'vazia' }
  | { tipo: 'valida'; minutos: number }
  | { tipo: 'invalida'; mensagem: string };

const HORA = '(?:h|hr|hrs|hora|horas)';
const MINUTO = '(?:m|min|mins|minuto|minutos)';

export function lerDuracao(texto: string): LeituraDuracao {
  const limpo = texto
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, ' ');
  if (!limpo) return { tipo: 'vazia' };

  let minutos: number | null = null;
  let partes: RegExpExecArray | null;

  if ((partes = /^(\d{1,2}):(\d{2})$/.exec(limpo))) {
    // 1:30
    const m = Number(partes[2]);
    if (m < 60) minutos = Number(partes[1]) * 60 + m;
  } else if (
    (partes = new RegExp(`^(\\d{1,2})\\s*${HORA}\\s*(?:e\\s*)?(\\d{1,2})\\s*(?:${MINUTO})?$`).exec(limpo))
  ) {
    // 1h30, 1h 30min, 1 hora e 30 minutos
    const m = Number(partes[2]);
    if (m < 60) minutos = Number(partes[1]) * 60 + m;
  } else if ((partes = new RegExp(`^(\\d{1,2}(?:[.,]\\d{1,2})?)\\s*${HORA}$`).exec(limpo))) {
    // 1h, 2 horas, 1,5h
    minutos = Math.round(Number(partes[1].replace(',', '.')) * 60);
  } else if ((partes = new RegExp(`^(\\d{1,3})\\s*(?:${MINUTO})?$`).exec(limpo))) {
    // 45, 45 min
    minutos = Number(partes[1]);
  }

  if (minutos === null || !Number.isFinite(minutos)) {
    return { tipo: 'invalida', mensagem: `Não entendi essa duração. ${EXEMPLO_DURACAO}.` };
  }
  if (minutos < DURACAO_MINIMA || minutos > DURACAO_MAXIMA) {
    return {
      tipo: 'invalida',
      mensagem: 'A duração precisa ficar entre 15 minutos e 8 horas. Se não souber, deixe em branco.',
    };
  }
  return { tipo: 'valida', minutos };
}

/** Forma normalizada, a mesma usada para exibir: 45 min, 1h, 1h30. */
export function formatarDuracao(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto ? `${horas}h${String(resto).padStart(2, '0')}` : `${horas}h`;
}
