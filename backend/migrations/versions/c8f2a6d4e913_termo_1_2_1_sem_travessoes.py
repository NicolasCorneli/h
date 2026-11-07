"""termo 1.2.1: a mesma 1.2, sem travessões

Uma pessoa que participou dos testes apontou travessões longos (—) no termo. A regra de
redação do projeto é não usá-los nos textos que o usuário lê, e o termo 1.2 tinha quatro:
um no termo do cliente e três no termo do profissional. Esta versão troca cada um pela
pontuação comum equivalente (`TROCAS`) e não muda mais nada: nem o que o termo informa,
nem o que o cliente autoriza. Um teste (`tests/test_termo_1_2_1.py`) confere que o texto
é o da 1.2 com exatamente essas trocas.

Por que uma versão nova, e não corrigir a 1.2: o texto já apresentado é imutável (o
gatilho de imutabilidade recusa a alteração), e cada consentimento continua apontando
para a versão que o cliente de fato leu.

Por que 1.2.1, e não 1.3: o terceiro número marca revisão só de redação. A regra de
revalidação compara apenas "maior.menor" (`regras_consentimento.conteudo_da_versao`):
quem aceitou a 1.2 não precisa decidir de novo, porque leu o mesmo conteúdo, e o mesmo vale
para a ciência do profissional. Quem aceitou a 1.1 ou antes continua precisando revalidar.

Nenhum registro de consentimento é alterado ou removido por esta migration.

Revision ID: c8f2a6d4e913
Revises: b5c8e1d3a742
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import date

from alembic import op
import sqlalchemy as sa

revision: str = "c8f2a6d4e913"
down_revision: str | None = "b5c8e1d3a742"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSAO_ANTERIOR = "1.2"

#: Cada travessão da 1.2 e a pontuação que o substitui. Nada além disto mudou.
TROCAS = [('normalmente — eles não dependem deste consentimento.',
  'normalmente: eles não dependem deste consentimento.'),
 ('deixe que ele leia — ou leia em voz alta para ele.',
  'deixe que ele leia, ou leia em voz alta para ele.'),
 ('antes de decidir — o termo traz o texto completo.',
  'antes de decidir. O termo traz o texto completo.'),
 ('agenda normais — apenas sem simulação.', 'agenda normais, apenas sem simulação.')]

TERMOS = [{'tipo': 'cliente',
  'versao': '1.2.1',
  'vigente_desde': '2026-11-07',
  'vigente': True,
  'titulo': 'Uso da sua foto na simulação de cabelo',
  'resumo': 'Para mostrar como ficaria o corte ou a cor antes de fazer, o aplicativo '
            'precisa tirar uma foto do seu rosto. Leia o que acontece com essa foto e '
            'decida com calma.',
  'secoes': [{'titulo': 'A foto do seu rosto é um dado sensível',
              'texto': 'Uma foto que mostra o seu rosto identifica você. Por isso ela só é '
                       'usada se você concordar de forma específica, aqui e agora, e só '
                       'para a finalidade descrita neste termo.',
              'destaque': True},
             {'titulo': 'Para que a foto é usada',
              'texto': 'Apenas para gerar uma simulação de corte, comprimento ou cor de '
                       'cabelo, que serve para você e o profissional conversarem antes de '
                       'executar o serviço. A imagem simulada também é uma imagem sua e '
                       'recebe o mesmo cuidado da foto original. Ela leva uma marca '
                       'invisível, colocada pelo Google, que mostra que foi feita por '
                       'inteligência artificial.'},
             {'titulo': 'A foto passa por duas empresas para gerar a simulação',
              'texto': 'O aplicativo não cria a prévia sozinho. A sua foto vai para a '
                       'Replicate, uma empresa de serviços de inteligência artificial. A '
                       'Replicate envia a foto ao Google, que é quem desenha o cabelo '
                       'novo, com um programa de inteligência artificial dele. Sem esse '
                       'envio não existe simulação. Vão apenas a sua foto e as escolhas do '
                       'atendimento: o corte, o gênero do corte e a cor. Seu nome, seu '
                       'telefone, sua data de nascimento e as observações do profissional '
                       'não são enviados.',
              'destaque': True},
             {'titulo': 'O que essas empresas podem fazer com a sua foto',
              'texto': 'A Replicate diz que apaga a foto e a simulação cerca de uma hora '
                       'depois. O Google guarda o que recebe por um tempo, para verificar '
                       'se houve uso proibido. Dependendo do contrato entre a Replicate e '
                       'o Google, que não é público, o Google também pode usar a sua foto '
                       'e a simulação para melhorar e treinar os próprios programas de '
                       'inteligência artificial, e pessoas da equipe dele podem vê-las '
                       'para isso. A foto pode ser processada fora do Brasil. Essas '
                       'permissões são dadas nos termos dessas empresas, e não por este '
                       'aplicativo nem pelo profissional que o utiliza. Depois que a '
                       'imagem sai daqui, não temos como controlar por quanto tempo ela '
                       'fica guardada nem com quem é compartilhada, e os termos dessas '
                       'empresas podem mudar. Se isso não lhe parecer aceitável, recuse: '
                       'seu atendimento continua normal.',
              'destaque': True},
             {'titulo': 'Onde a foto fica guardada aqui',
              'texto': 'A foto original e a simulação ficam vinculadas ao seu cadastro, '
                       'visíveis apenas para o profissional que registrou este '
                       'consentimento, enquanto você for cliente dele ou até que a '
                       'exclusão seja solicitada.'},
             {'titulo': 'Recusar não muda o seu atendimento',
              'texto': 'Você pode recusar. Seu cadastro, seu histórico de atendimentos e '
                       'seus agendamentos continuam funcionando normalmente: eles não '
                       'dependem deste consentimento. A única coisa que deixa de existir é '
                       'a simulação por inteligência artificial.'},
             {'titulo': 'Você pode mudar de ideia quando quiser',
              'texto': 'A qualquer momento você pode pedir ao profissional que cancele '
                       'este consentimento. O cancelamento é imediato, bloqueia novas '
                       'fotos e permite apagar as simulações já guardadas. Não é preciso '
                       'justificar.'},
             {'titulo': 'Se você tem menos de 18 anos',
              'texto': 'O consentimento precisa ser dado por um dos pais ou pelo '
                       'responsável legal, que deve estar presente e se identificar no '
                       'registro.'}]},
 {'tipo': 'profissional',
  'versao': '1.2.1',
  'vigente_desde': '2026-11-07',
  'vigente': True,
  'titulo': 'Suas responsabilidades ao usar a simulação',
  'resumo': 'Quem responde pelo tratamento das imagens dos seus clientes é você. O '
            'aplicativo registra as decisões, mas a conversa com o cliente é sua.',
  'secoes': [{'titulo': 'Explique antes de registrar',
              'texto': 'Antes de marcar qualquer decisão no app, apresente o termo ao '
                       'cliente e deixe que ele leia, ou leia em voz alta para ele. '
                       'Registrar um aceite que o cliente não deu invalida o consentimento '
                       'e a responsabilidade é sua.',
              'destaque': True},
             {'titulo': 'Diga que a foto passa pela Replicate e pelo Google, e o que eles '
                        'podem fazer',
              'texto': 'Antes de registrar a decisão, explique ao cliente que a foto é '
                       'enviada à Replicate, que a repassa ao Google para gerar a prévia '
                       'com inteligência artificial. Diga que essas empresas podem guardar '
                       'a foto por um tempo e que, conforme o contrato entre elas, o '
                       'Google pode usar as imagens recebidas e geradas para melhorar e '
                       'treinar os sistemas dele. Diga também o que não é enviado: nome, '
                       'telefone, data de nascimento e observações ficam no aplicativo. O '
                       'cliente precisa saber disso antes de decidir. O termo traz o texto '
                       'completo.',
              'destaque': True},
             {'titulo': 'Cada cliente decide por si',
              'texto': 'O consentimento é individual: vale para um cliente, não para a sua '
                       'carteira. Um cliente que recusou continua com cadastro, histórico '
                       'e agenda normais, apenas sem simulação.'},
             {'titulo': 'Menores de idade',
              'texto': 'Quando o cliente tem menos de 18 anos, quem consente é um dos pais '
                       'ou o responsável legal, que precisa estar presente no momento do '
                       'registro e se identificar.'},
             {'titulo': 'Cancelamento é direito do cliente',
              'texto': 'Se o cliente pedir para cancelar, faça na hora, pelo perfil dele. '
                       'Cancelar é tão simples quanto aceitar, e você pode apagar as '
                       'imagens já guardadas no mesmo lugar.'}]}]

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
            {"tipo": termo["tipo"], "anterior": VERSAO_ANTERIOR},
        )
