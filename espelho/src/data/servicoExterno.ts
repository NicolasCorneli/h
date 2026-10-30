/**
 * Fonte única dos textos sobre o serviço externo de inteligência artificial.
 *
 * Antes, cada tela escrevia a sua própria versão do mesmo assunto, e elas começaram a
 * divergir. Aqui ficam as frases que o profissional lê — a tela de privacidade, o aviso
 * antes de gerar a simulação e o resumo do resultado. O texto apresentado ao cliente é
 * outro: vive no banco, em `termos`, versionado e imutável, porque é o documento sobre o
 * qual ele manifesta a decisão.
 *
 * Regra ao editar: só entra aqui o que pode ser sustentado por uma destas três fontes:
 *
 * 1. o que o código faz, e que os testes comprovam;
 * 2. os termos publicados pelo fornecedor;
 * 3. a configuração efetiva do servidor.
 *
 * Nada de garantia de privacidade que o sistema não possa cumprir nem verificar. Se uma
 * informação não puder ser confirmada, ela é apresentada como o que é — o que o
 * fornecedor declara, e não o que nós garantimos.
 */

/** Nome que o profissional vê. Evita jargão: não é "provedor de IA" nem "endpoint". */
export const SERVICO_EXTERNO = 'serviço de inteligência artificial';

export const USO_DE_DADOS = {
  /** Para que serve o envio. */
  finalidade:
    'Gerar a imagem da simulação. O aplicativo não cria a prévia sozinho: quem desenha o cabelo novo sobre a foto é um serviço de inteligência artificial de outra empresa, contratado para isso.',

  /** O que sai do sistema — verificado por teste automatizado da suíte. */
  oQueSai:
    'Sai a foto do cliente e as escolhas do atendimento: o corte, o gênero do corte (feminino, masculino ou não especificado) e a cor. Nada mais. Nome, telefone, data de nascimento e observações ficam guardados no aplicativo e nunca acompanham a imagem.',

  /** Por que é necessário. */
  porQue:
    'Sem a foto, não há o que simular: a imagem gerada parte do rosto e do cabelo do cliente. Sem o corte e a cor, o serviço não sabe o que desenhar.',

  /** O que a empresa pode fazer com a imagem, segundo os termos dela. */
  oQueElaPodeFazer:
    'Os termos de uso dessa empresa permitem que ela utilize as imagens recebidas e as geradas para operar e melhorar os serviços dela, inclusive para treinar os próprios modelos de inteligência artificial. Essa permissão é dada nos termos dela, não por este aplicativo.',

  /** O limite honesto do que o aplicativo pode prometer. */
  oQueNaoControlamos:
    'Depois que a imagem sai daqui, o aplicativo não controla por quanto tempo ela fica guardada nem com quem é compartilhada. Quem define isso é a empresa que presta o serviço, nos termos dela, que podem mudar.',

  /** O que depende da decisão do cliente, e é imposto pelo servidor. */
  consentimento:
    'Nenhuma foto é enviada sem que o cliente tenha respondido ao termo e autorizado o uso da própria imagem. O bloqueio é do próprio sistema: sem autorização registrada, a simulação nem começa.',

  /** O que o aplicativo faz de fato com as imagens que guarda. */
  dentroDoApp:
    'Dentro do aplicativo, as imagens ficam ligadas apenas à sua conta e abrem por um link temporário, que expira em poucos minutos. Excluir o cliente, ou a conta, apaga as imagens.',
} as const;

/** Resumo curto, para avisos onde não cabe o texto inteiro. */
export const RESUMO_ENVIO =
  'Para gerar a prévia, a foto e as escolhas de corte, gênero e cor vão para um serviço de inteligência artificial de outra empresa. Nome, telefone e observações do cliente não são enviados.';
