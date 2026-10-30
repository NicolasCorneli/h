"""termo 1.1: o que o serviço externo pode fazer com a foto

A versão 1.0 dizia que não sabíamos se a empresa terceira usaria a imagem para treinar os
modelos dela. Passamos a saber: os termos publicados pelo fornecedor permitem esse uso.
Declarar incerteza quando existe conhecimento é informar pior do que se pode — e o art. 9º
da LGPD exige informação clara e adequada sobre a finalidade do tratamento.

Publicar uma versão nova é o caminho previsto: o texto já apresentado é imutável, e cada
decisão registrada continua apontando para a versão que o cliente de fato leu. Como a
versão vigente muda, todo consentimento aceito sobre a 1.0 passa a exigir revalidação
antes da próxima foto — que é exatamente o efeito desejado quando a informação muda.

Nenhum registro de consentimento é alterado ou removido por esta migration.

Revision ID: c3f1a2d45e60
Revises: b1a7c0dfe201
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import date

from alembic import op
import sqlalchemy as sa

revision: str = "c3f1a2d45e60"
down_revision: str | None = "b1a7c0dfe201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TERMOS = [   {   'tipo': 'cliente',
        'versao': '1.1',
        'vigente_desde': '2026-10-21',
        'vigente': True,
        'titulo': 'Uso da sua foto na simulação de cabelo',
        'resumo': 'Para mostrar como ficaria o corte ou a cor antes de fazer, o aplicativo '
                  'precisa tirar uma foto do seu rosto. Leia o que acontece com essa foto e '
                  'decida com calma.',
        'secoes': [   {   'titulo': 'A foto do seu rosto é um dado sensível',
                          'texto': 'Uma foto que mostra o seu rosto identifica você. Por isso '
                                   'ela só é usada se você concordar de forma específica, aqui '
                                   'e agora, e só para a finalidade descrita neste termo.',
                          'destaque': True},
                      {   'titulo': 'Para que a foto é usada',
                          'texto': 'Apenas para gerar uma simulação de corte, comprimento ou '
                                   'cor de cabelo, que serve para você e o profissional '
                                   'conversarem antes de executar o serviço. A imagem simulada '
                                   'também é uma imagem sua e recebe o mesmo cuidado da foto '
                                   'original.'},
                      {   'titulo': 'A foto vai para outra empresa gerar a simulação',
                          'texto': 'O aplicativo não cria a prévia sozinho. Quem desenha o '
                                   'cabelo novo sobre a sua foto é um serviço de inteligência '
                                   'artificial de outra empresa, contratado para isso. Sem '
                                   'esse envio não existe simulação. Vão apenas a sua foto e '
                                   'as duas escolhas do atendimento — o corte e a cor. Seu '
                                   'nome, seu telefone, sua data de nascimento e as '
                                   'observações do profissional não são enviados.',
                          'destaque': True},
                      {   'titulo': 'Essa empresa pode usar a sua foto para treinar os '
                                    'sistemas dela',
                          'texto': 'Os termos de uso dessa empresa permitem que ela utilize as '
                                   'imagens que recebe e as que gera para operar e melhorar os '
                                   'serviços dela, inclusive para treinar os próprios '
                                   'programas de inteligência artificial. Essa permissão é '
                                   'dada nos termos dela, e não por este aplicativo nem pelo '
                                   'profissional que o utiliza. Depois que a imagem sai daqui, '
                                   'não temos como controlar por quanto tempo ela fica '
                                   'guardada nem com quem é compartilhada, e os termos dessa '
                                   'empresa podem mudar. Se isso não lhe parecer aceitável, '
                                   'recuse: seu atendimento continua normal.',
                          'destaque': True},
                      {   'titulo': 'Onde a foto fica guardada aqui',
                          'texto': 'A foto original e a simulação ficam vinculadas ao seu '
                                   'cadastro, visíveis apenas para o profissional que '
                                   'registrou este consentimento, enquanto você for cliente '
                                   'dele ou até que a exclusão seja solicitada.'},
                      {   'titulo': 'Recusar não muda o seu atendimento',
                          'texto': 'Você pode recusar. Seu cadastro, seu histórico de '
                                   'atendimentos e seus agendamentos continuam funcionando '
                                   'normalmente — eles não dependem deste consentimento. A '
                                   'única coisa que deixa de existir é a simulação por '
                                   'inteligência artificial.'},
                      {   'titulo': 'Você pode mudar de ideia quando quiser',
                          'texto': 'A qualquer momento você pode pedir ao profissional que '
                                   'cancele este consentimento. O cancelamento é imediato, '
                                   'bloqueia novas fotos e permite apagar as simulações já '
                                   'guardadas. Não é preciso justificar.'},
                      {   'titulo': 'Se você tem menos de 18 anos',
                          'texto': 'O consentimento precisa ser dado por um dos pais ou pelo '
                                   'responsável legal, que deve estar presente e se '
                                   'identificar no registro.'}]},
    {   'tipo': 'profissional',
        'versao': '1.1',
        'vigente_desde': '2026-10-21',
        'vigente': True,
        'titulo': 'Suas responsabilidades ao usar a simulação',
        'resumo': 'Quem responde pelo tratamento das imagens dos seus clientes é você. O '
                  'aplicativo registra as decisões, mas a conversa com o cliente é sua.',
        'secoes': [   {   'titulo': 'Explique antes de registrar',
                          'texto': 'Antes de marcar qualquer decisão no app, apresente o termo '
                                   'ao cliente e deixe que ele leia — ou leia em voz alta para '
                                   'ele. Registrar um aceite que o cliente não deu invalida o '
                                   'consentimento e a responsabilidade é sua.',
                          'destaque': True},
                      {   'titulo': 'Diga que a foto vai para outra empresa, e o que ela pode '
                                    'fazer',
                          'texto': 'Antes de registrar a decisão, explique ao cliente que a '
                                   'foto é enviada a um serviço de inteligência artificial de '
                                   'outra empresa para gerar a prévia, e que os termos dessa '
                                   'empresa permitem que ela use as imagens recebidas e '
                                   'geradas para melhorar e treinar os sistemas dela. Diga '
                                   'também o que não é enviado: nome, telefone, data de '
                                   'nascimento e observações ficam no aplicativo. O cliente '
                                   'precisa saber disso antes de decidir — o termo traz o '
                                   'texto completo.',
                          'destaque': True},
                      {   'titulo': 'Cada cliente decide por si',
                          'texto': 'O consentimento é individual: vale para um cliente, não '
                                   'para a sua carteira. Um cliente que recusou continua com '
                                   'cadastro, histórico e agenda normais — apenas sem '
                                   'simulação.'},
                      {   'titulo': 'Menores de idade',
                          'texto': 'Quando o cliente tem menos de 18 anos, quem consente é um '
                                   'dos pais ou o responsável legal, que precisa estar '
                                   'presente no momento do registro e se identificar.'},
                      {   'titulo': 'Cancelamento é direito do cliente',
                          'texto': 'Se o cliente pedir para cancelar, faça na hora, pelo '
                                   'perfil dele. Cancelar é tão simples quanto aceitar, e você '
                                   'pode apagar as imagens já guardadas no mesmo lugar.'}]}]


def upgrade() -> None:
    conexao = op.get_bind()
    for termo in TERMOS:
        # A versão anterior do mesmo tipo deixa de ser a vigente. O texto dela permanece
        # no banco: é o documento que os clientes anteriores leram, e o gatilho de
        # imutabilidade impede qualquer alteração no conteúdo.
        conexao.execute(
            sa.text("UPDATE termos SET vigente = false WHERE tipo = :tipo AND vigente = true"),
            {"tipo": termo["tipo"]},
        )
        conexao.execute(
            sa.text(
                """
                INSERT INTO termos
                    (id, tipo, versao, vigente_desde, vigente, titulo, resumo, secoes, criado_em)
                VALUES
                    (:id, :tipo, :versao, :vigente_desde, :vigente, :titulo, :resumo,
                     CAST(:secoes AS jsonb), now())
                """
            ),
            {
                "id": uuid.uuid4(),
                "tipo": termo["tipo"],
                "versao": termo["versao"],
                "vigente_desde": date.fromisoformat(termo["vigente_desde"]),
                "vigente": termo["vigente"],
                "titulo": termo["titulo"],
                "resumo": termo["resumo"],
                "secoes": json.dumps(termo["secoes"], ensure_ascii=False),
            },
        )


def downgrade() -> None:
    conexao = op.get_bind()
    for termo in TERMOS:
        # Recusa-se a remover uma versão que já serviu de base para alguma decisão: o
        # vínculo entre consentimento e texto apresentado é o que sustenta o art. 37.
        em_uso = conexao.execute(
            sa.text(
                """
                SELECT count(*) FROM consentimentos c
                JOIN termos t ON t.id = c.termo_id
                WHERE t.tipo = :tipo AND t.versao = :versao
                """
            ),
            {"tipo": termo["tipo"], "versao": termo["versao"]},
        ).scalar_one()
        if em_uso:
            raise RuntimeError(
                f"a versao {termo['versao']} do termo de {termo['tipo']} ja foi apresentada "
                f"a {em_uso} cliente(s) e nao pode ser removida"
            )
        conexao.execute(
            sa.text("DELETE FROM termos WHERE tipo = :tipo AND versao = :versao"),
            {"tipo": termo["tipo"], "versao": termo["versao"]},
        )
        conexao.execute(
            sa.text(
                "UPDATE termos SET vigente = true WHERE tipo = :tipo AND versao = :anterior"
            ),
            {"tipo": termo["tipo"], "anterior": "1.0"},
        )
