import { formatarDuracao } from './duracao';

const DIAS = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
const MESES = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
];
const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

const doisDigitos = (n: number) => String(n).padStart(2, '0');

export function paraData(iso: string): Date {
  // Uma data sem hora ("2026-10-19", como a data do serviço e o nascimento) é um dia do
  // calendário, não um instante. `new Date` a leria como meia-noite em Greenwich, que no
  // Brasil ainda é o dia anterior: o atendimento de 19/10 apareceria como 18/10.
  const soData = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (soData) return new Date(Number(soData[1]), Number(soData[2]) - 1, Number(soData[3]));
  return new Date(iso);
}

/** "2026-10-19": o dia no calendário do aparelho, sem passar por Greenwich. */
export function diaLocalIso(data: Date = new Date()): string {
  return `${data.getFullYear()}-${doisDigitos(data.getMonth() + 1)}-${doisDigitos(data.getDate())}`;
}

/** "Quinta, 12 de março" */
export function diaPorExtenso(iso: string): string {
  const d = paraData(iso);
  return `${DIAS[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]}`;
}

/** "12 de março de 2026" */
export function dataPorExtenso(iso: string): string {
  const d = paraData(iso);
  return `${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
}

/** "12/03" */
export function diaMes(iso: string): string {
  const d = paraData(iso);
  return `${doisDigitos(d.getDate())}/${doisDigitos(d.getMonth() + 1)}`;
}

/** "12/03/2026" */
export function dataCurta(iso: string): string {
  const d = paraData(iso);
  return `${doisDigitos(d.getDate())}/${doisDigitos(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/** "04 mar" */
export function diaMesCurto(iso: string): string {
  const d = paraData(iso);
  return `${doisDigitos(d.getDate())} ${MESES_CURTOS[d.getMonth()]}`;
}

/** "14:30" */
export function hora(iso: string): string {
  const d = paraData(iso);
  return `${doisDigitos(d.getHours())}:${doisDigitos(d.getMinutes())}`;
}

export function nomeDoMes(iso: string): string {
  const d = paraData(iso);
  const nome = MESES[d.getMonth()];
  return nome.charAt(0).toUpperCase() + nome.slice(1);
}

export function mesmoDia(a: string, b: string): boolean {
  const x = paraData(a);
  const y = paraData(b);
  return (
    x.getFullYear() === y.getFullYear() && x.getMonth() === y.getMonth() && x.getDate() === y.getDate()
  );
}

/** "em 45 min", "em 2h10", "amanhã", "quinta" ou "há 20 min" para horários passados. */
export function distanciaAteAgora(iso: string, agora = new Date()): string {
  const alvo = paraData(iso);
  const diffMin = Math.round((alvo.getTime() - agora.getTime()) / 60000);
  if (Math.abs(diffMin) < 2) return 'agora';

  const diaAlvo = new Date(alvo.getFullYear(), alvo.getMonth(), alvo.getDate());
  const diaHoje = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
  const diasDeDiferenca = Math.round((diaAlvo.getTime() - diaHoje.getTime()) / 86400000);

  // O cartão do próximo atendimento já mostra a data por extenso; aqui vai só a distância.
  // Dentro de 24 horas, em horas e minutos; além disso, em dias (sem repetir o dia da semana).
  if (diasDeDiferenca < 0) return diaMesCurto(iso);
  if (diffMin >= 24 * 60) return `em ${diasDeDiferenca} ${diasDeDiferenca === 1 ? 'dia' : 'dias'}`;

  const abs = Math.abs(diffMin);
  const texto = abs < 60 ? `${abs} min` : `${Math.floor(abs / 60)}h${abs % 60 ? doisDigitos(abs % 60) : ''}`;
  return diffMin > 0 ? `em ${texto}` : `há ${texto}`;
}

export function saudacao(agora = new Date()): string {
  const h = agora.getHours();
  if (h < 12) return 'Bom dia';
  if (h < 18) return 'Boa tarde';
  return 'Boa noite';
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/);
  const primeira = partes[0]?.[0] ?? '';
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : '';
  return (primeira + ultima).toUpperCase();
}

/**
 * Converte "12/03/2026" em "2026-03-12"; devolve null quando o texto não é uma data válida.
 *
 * Devolve o dia do calendário, sem hora. Antes devolvia um instante
 * ("2026-03-12T15:00:00.000Z"), que o servidor recusa para um campo de data: cadastrar
 * ou editar cliente com data de nascimento falhava sempre.
 */
export function isoDeDataCurta(texto: string): string | null {
  const partes = texto.trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!partes) return null;

  const [, dia, mes, ano] = partes;
  const data = new Date(Number(ano), Number(mes) - 1, Number(dia), 12, 0, 0, 0);
  if (Number.isNaN(data.getTime())) return null;
  if (data.getDate() !== Number(dia) || data.getMonth() !== Number(mes) - 1) return null;
  return diaLocalIso(data);
}

/** Data ISO deslocada em dias/horas a partir de hoje — usada só pelos dados de exemplo. */
export function emRelacaoAHoje(dias: number, horas = 9, minutos = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  d.setHours(horas, minutos, 0, 0);
  return d.toISOString();
}

/** Duração legível: 45 min, 1h, 1h30. A mesma forma em que o campo de duração a mostra. */
export function duracao(min: number): string {
  return formatarDuracao(min);
}

