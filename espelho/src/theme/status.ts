import type { StatusAgendamento } from '@/data/tipos';

import type { NomeIcone } from '@/components/Icone';

import { cores } from './tokens';

/**
 * Aparência de cada situação de agendamento, a mesma em todas as telas.
 *
 * A cor nunca vem sozinha: cada situação tem também ícone e texto próprios (WCAG 1.4.1).
 */
export const TOM_STATUS: Record<
  StatusAgendamento,
  { faixa: string; selo: 'sucesso' | 'alerta' | 'concluido' | 'erro'; icone: NomeIcone }
> = {
  pendente: { faixa: cores.alerta, selo: 'alerta', icone: 'relogio' },
  confirmado: { faixa: cores.sucesso, selo: 'sucesso', icone: 'ok' },
  concluido: { faixa: cores.concluido, selo: 'concluido', icone: 'okCirculo' },
  cancelado: { faixa: cores.bordaForte, selo: 'erro', icone: 'proibido' },
};
