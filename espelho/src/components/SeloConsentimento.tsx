import type { ConsentimentoStatus } from '@/data/tipos';

import { Selo } from './Basicos';
import type { NomeIcone } from './Icone';

type Props = {
  status: ConsentimentoStatus;
  /** Aceite dado sobre uma versão anterior do termo. */
  revalidar?: boolean;
  compacto?: boolean;
};

/**
 * Estado do consentimento de imagem. Cada estado combina cor, ícone e texto: a
 * informação nunca depende só da cor (WCAG 1.4.1).
 */
const ESTILO: Record<
  ConsentimentoStatus,
  { tom: 'sucesso' | 'alerta' | 'erro'; icone: NomeIcone; longo: string; curto: string }
> = {
  aceito: { tom: 'sucesso', icone: 'okCirculo', longo: 'Imagem autorizada', curto: 'uso de imagem autorizado' },
  pendente: { tom: 'alerta', icone: 'relogio', longo: 'Consentimento pendente', curto: 'uso de imagem pendente' },
  recusado: { tom: 'erro', icone: 'proibido', longo: 'Uso de imagem recusado', curto: 'uso de imagem recusado' },
  revogado: { tom: 'erro', icone: 'proibido', longo: 'Consentimento cancelado', curto: 'uso de imagem cancelado' },
};

const REVALIDAR = {
  tom: 'alerta' as const,
  icone: 'alerta' as NomeIcone,
  longo: 'Aceito em versão anterior',
  curto: 'uso de imagem a renovar',
};

export function SeloConsentimento({ status, revalidar = false, compacto = false }: Props) {
  const estilo = revalidar ? REVALIDAR : ESTILO[status];
  return <Selo texto={compacto ? estilo.curto : estilo.longo} tom={estilo.tom} icone={estilo.icone} />;
}
