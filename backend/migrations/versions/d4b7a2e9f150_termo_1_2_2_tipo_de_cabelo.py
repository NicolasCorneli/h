"""termo 1.2.2 do cliente: a lista do que é enviado inclui o tipo de cabelo desejado

Desde a migration c7d3f9a1e64b, a etapa "Estilo e cor" pergunta o tipo de cabelo desejado
na simulação (1A a 4C, ou manter o atual), e essa escolha entra na instrução enviada à
Replicate. O termo 1.2.1 do cliente diz que vão "a sua foto e as escolhas do atendimento:
o corte, o gênero do corte e a cor". A lista ficou incompleta, e o nome da opção mudou na
tela ("Estilo do corte", com Feminino, Masculino e Neutro). Esta versão troca só essa frase
(`TROCAS`); um teste (`tests/test_termo_1_2_2.py`) confere que o resto é o texto da 1.2.1.

Por que 1.2.2, e não 1.3: a regra de revalidação compara apenas "maior.menor"
(`regras_consentimento.conteudo_da_versao`), e o terceiro número marca uma revisão que não
muda o que o cliente autoriza. É o caso: a foto enviada, a finalidade, as empresas que a
recebem e o que elas podem fazer continuam iguais. O tipo de cabelo é mais uma escolha do
atendimento, como o corte e a cor, e não é dado pessoal do cliente: o nome, o telefone, a
data de nascimento e as observações continuam de fora. Quem aceitou a 1.2 ou a 1.2.1 não
precisa decidir de novo; quem aceitou a 1.1 ou antes continua precisando.

O termo do profissional não muda: ele não lista as escolhas enviadas e continua na 1.2.1.

Por que uma versão nova, e não corrigir a 1.2.1: o texto já apresentado é imutável (o
gatilho de imutabilidade recusa a alteração), e cada consentimento continua apontando para
a versão que o cliente de fato leu.

Nenhum registro de consentimento é alterado ou removido por esta migration.

Revision ID: d4b7a2e9f150
Revises: c7d3f9a1e64b
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import date

from alembic import op
import sqlalchemy as sa

revision: str = "d4b7a2e9f150"
down_revision: str | None = "c7d3f9a1e64b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSAO_ANTERIOR = "1.2.1"

#: A única frase da 1.2.1 que muda, e o texto que a substitui.
TROCAS = [
    (
        "atendimento: o corte, o gênero do corte e a cor.",
        "atendimento: o corte, o estilo do corte, a cor e o tipo de cabelo desejado.",
    )
]

TERMO = {'tipo': 'cliente',
 'versao': '1.2.2',
 'vigente_desde': '2026-11-10',
 'vigente': True,
 'titulo': 'Uso da sua foto na simulação de cabelo',
 'resumo': 'Para mostrar como ficaria o corte ou a cor antes de fazer, o aplicativo precisa '
           'tirar uma foto do seu rosto. Leia o que acontece com essa foto e decida com '
           'calma.',
 'secoes': [{'titulo': 'A foto do seu rosto é um dado sensível',
             'texto': 'Uma foto que mostra o seu rosto identifica você. Por isso ela só é '
                      'usada se você concordar de forma específica, aqui e agora, e só para a '
                      'finalidade descrita neste termo.',
             'destaque': True},
            {'titulo': 'Para que a foto é usada',
             'texto': 'Apenas para gerar uma simulação de corte, comprimento ou cor de '
                      'cabelo, que serve para você e o profissional conversarem antes de '
                      'executar o serviço. A imagem simulada também é uma imagem sua e recebe '
                      'o mesmo cuidado da foto original. Ela leva uma marca invisível, '
                      'colocada pelo Google, que mostra que foi feita por inteligência '
                      'artificial.'},
            {'titulo': 'A foto passa por duas empresas para gerar a simulação',
             'texto': 'O aplicativo não cria a prévia sozinho. A sua foto vai para a '
                      'Replicate, uma empresa de serviços de inteligência artificial. A '
                      'Replicate envia a foto ao Google, que é quem desenha o cabelo novo, '
                      'com um programa de inteligência artificial dele. Sem esse envio não '
                      'existe simulação. Vão apenas a sua foto e as escolhas do atendimento: '
                      'o corte, o estilo do corte, a cor e o tipo de cabelo desejado. Seu '
                      'nome, seu telefone, sua data de nascimento e as observações do '
                      'profissional não são enviados.',
             'destaque': True},
            {'titulo': 'O que essas empresas podem fazer com a sua foto',
             'texto': 'A Replicate diz que apaga a foto e a simulação cerca de uma hora '
                      'depois. O Google guarda o que recebe por um tempo, para verificar se '
                      'houve uso proibido. Dependendo do contrato entre a Replicate e o '
                      'Google, que não é público, o Google também pode usar a sua foto e a '
                      'simulação para melhorar e treinar os próprios programas de '
                      'inteligência artificial, e pessoas da equipe dele podem vê-las para '
                      'isso. A foto pode ser processada fora do Brasil. Essas permissões são '
                      'dadas nos termos dessas empresas, e não por este aplicativo nem pelo '
                      'profissional que o utiliza. Depois que a imagem sai daqui, não temos '
                      'como controlar por quanto tempo ela fica guardada nem com quem é '
                      'compartilhada, e os termos dessas empresas podem mudar. Se isso não '
                      'lhe parecer aceitável, recuse: seu atendimento continua normal.',
             'destaque': True},
            {'titulo': 'Onde a foto fica guardada aqui',
             'texto': 'A foto original e a simulação ficam vinculadas ao seu cadastro, '
                      'visíveis apenas para o profissional que registrou este consentimento, '
                      'enquanto você for cliente dele ou até que a exclusão seja solicitada.'},
            {'titulo': 'Recusar não muda o seu atendimento',
             'texto': 'Você pode recusar. Seu cadastro, seu histórico de atendimentos e seus '
                      'agendamentos continuam funcionando normalmente: eles não dependem '
                      'deste consentimento. A única coisa que deixa de existir é a simulação '
                      'por inteligência artificial.'},
            {'titulo': 'Você pode mudar de ideia quando quiser',
             'texto': 'A qualquer momento você pode pedir ao profissional que cancele este '
                      'consentimento. O cancelamento é imediato, bloqueia novas fotos e '
                      'permite apagar as simulações já guardadas. Não é preciso justificar.'},
            {'titulo': 'Se você tem menos de 18 anos',
             'texto': 'O consentimento precisa ser dado por um dos pais ou pelo responsável '
                      'legal, que deve estar presente e se identificar no registro.'}]}



def upgrade() -> None:
    conexao = op.get_bind()
    # A 1.2.1 deixa de ser a vigente. O texto dela permanece no banco: é o documento que os
    # clientes anteriores leram, e o gatilho de imutabilidade impede qualquer alteração.
    conexao.execute(
        sa.text("UPDATE termos SET vigente = false WHERE tipo = :tipo AND vigente = true"),
        {"tipo": TERMO["tipo"]},
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
            "tipo": TERMO["tipo"],
            "versao": TERMO["versao"],
            "vigente_desde": date.fromisoformat(TERMO["vigente_desde"]),
            "vigente": TERMO["vigente"],
            "titulo": TERMO["titulo"],
            "resumo": TERMO["resumo"],
            "secoes": json.dumps(TERMO["secoes"], ensure_ascii=False),
        },
    )


def downgrade() -> None:
    conexao = op.get_bind()
    # Recusa-se a remover uma versão que já serviu de base para alguma decisão: o vínculo
    # entre consentimento e texto apresentado é o que sustenta o art. 37.
    em_uso = conexao.execute(
        sa.text(
            """
            SELECT count(*) FROM consentimentos c
            JOIN termos t ON t.id = c.termo_id
            WHERE t.tipo = :tipo AND t.versao = :versao
            """
        ),
        {"tipo": TERMO["tipo"], "versao": TERMO["versao"]},
    ).scalar_one()
    if em_uso:
        raise RuntimeError(
            f"a versao {TERMO['versao']} do termo de {TERMO['tipo']} ja foi apresentada "
            f"a {em_uso} cliente(s) e nao pode ser removida"
        )
    conexao.execute(
        sa.text("DELETE FROM termos WHERE tipo = :tipo AND versao = :versao"),
        {"tipo": TERMO["tipo"], "versao": TERMO["versao"]},
    )
    conexao.execute(
        sa.text("UPDATE termos SET vigente = true WHERE tipo = :tipo AND versao = :anterior"),
        {"tipo": TERMO["tipo"], "anterior": VERSAO_ANTERIOR},
    )
