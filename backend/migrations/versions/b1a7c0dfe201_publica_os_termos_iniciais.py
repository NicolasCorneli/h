"""publica os termos iniciais

Dados de sistema, não dados de demonstração: sem um termo vigente o aplicativo não pode
registrar consentimento algum. Os textos são exatamente os que o aplicativo exibia em
`src/data/termos.ts`, migrados para a tabela `termos` (achado A6 do diagnóstico).

Revision ID: b1a7c0dfe201
Revises: 3de36fc61782
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import date

from alembic import op
import sqlalchemy as sa

revision: str = "b1a7c0dfe201"
down_revision: str | None = "3de36fc61782"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TERMOS = [   {   'tipo': 'cliente',
        'versao': '1.0',
        'vigente_desde': '2026-09-16',
        'vigente': True,
        'titulo': 'Uso da sua foto na simulação de cabelo',
        'resumo': 'Para mostrar como ficaria o corte ou a cor antes de fazer, o aplicativo '
                  'precisa tirar uma foto do seu rosto. Leia o que acontece com essa foto e '
                  'decida com calma.',
        'secoes': [   {   'titulo': 'A foto do seu rosto é um dado sensível',
                          'texto': 'Uma foto que mostra o seu rosto identifica você. Por isso '
                                   'ela só é usada se você concordar de forma específica, aqui e '
                                   'agora, e só para a finalidade descrita neste termo.',
                          'destaque': True},
                      {   'titulo': 'Para que a foto é usada',
                          'texto': 'Apenas para gerar uma simulação de corte, comprimento ou cor '
                                   'de cabelo, que serve para você e o profissional conversarem '
                                   'antes de executar o serviço. A imagem simulada também é uma '
                                   'imagem sua e recebe o mesmo cuidado da foto original.'},
                      {   'titulo': 'A foto sai do aparelho e vai para outra empresa',
                          'texto': 'Para criar a simulação, a foto é enviada a um serviço de '
                                   'inteligência artificial operado por uma empresa terceira, '
                                   'fora deste aplicativo. Sem esse envio não é possível gerar a '
                                   'simulação.',
                          'destaque': True},
                      {   'titulo': 'O que não podemos garantir sobre essa empresa',
                          'texto': 'Não temos controle sobre o que a empresa terceira faz com a '
                                   'foto depois de recebê-la: por quanto tempo ela guarda a '
                                   'imagem, se a utiliza para treinar seus próprios modelos ou '
                                   'com quem a compartilha. Esses termos são definidos por ela, '
                                   'e não por este aplicativo nem pelo profissional que o '
                                   'utiliza.',
                          'destaque': True},
                      {   'titulo': 'Onde a foto fica guardada aqui',
                          'texto': 'A foto original e a simulação ficam vinculadas ao seu '
                                   'cadastro, visíveis apenas para o profissional que registrou '
                                   'este consentimento, enquanto você for cliente dele ou até '
                                   'que a exclusão seja solicitada.'},
                      {   'titulo': 'Recusar não muda o seu atendimento',
                          'texto': 'Você pode recusar. Seu cadastro, seu histórico de '
                                   'atendimentos e seus agendamentos continuam funcionando '
                                   'normalmente — eles não dependem deste consentimento. A única '
                                   'coisa que deixa de existir é a simulação por inteligência '
                                   'artificial.'},
                      {   'titulo': 'Você pode mudar de ideia quando quiser',
                          'texto': 'A qualquer momento você pode pedir ao profissional que '
                                   'cancele este consentimento. O cancelamento é imediato, '
                                   'bloqueia novas fotos e permite apagar as simulações já '
                                   'guardadas. Não é preciso justificar.'},
                      {   'titulo': 'Se você tem menos de 18 anos',
                          'texto': 'O consentimento precisa ser dado por um dos pais ou pelo '
                                   'responsável legal, que deve estar presente e se identificar '
                                   'no registro.'}]},
    {   'tipo': 'cliente',
        'versao': '0.9',
        'vigente_desde': '2026-05-04',
        'vigente': False,
        'titulo': 'Uso da sua foto na simulação de cabelo',
        'resumo': 'O aplicativo tira uma foto do seu rosto para simular um corte ou uma cor de '
                  'cabelo antes da execução do serviço.',
        'secoes': [   {   'titulo': 'Para que a foto é usada',
                          'texto': 'Apenas para gerar uma simulação de corte ou cor, que serve '
                                   'de apoio à conversa com o profissional antes do serviço.'},
                      {   'titulo': 'Processamento por inteligência artificial',
                          'texto': 'A imagem é processada por um serviço de inteligência '
                                   'artificial para gerar a simulação.'},
                      {   'titulo': 'Guarda e exclusão',
                          'texto': 'A foto e a simulação ficam vinculadas ao seu cadastro no '
                                   'aplicativo e podem ser excluídas a seu pedido.'},
                      {   'titulo': 'Cancelamento',
                          'texto': 'Você pode cancelar esta autorização a qualquer momento, '
                                   'pedindo ao profissional.'}]},
    {   'tipo': 'profissional',
        'versao': '1.0',
        'vigente_desde': '2026-09-16',
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
                      {   'titulo': 'Diga que a foto vai para uma empresa terceira',
                          'texto': 'A simulação depende de um serviço externo de inteligência '
                                   'artificial. Nem este aplicativo nem você controlam por '
                                   'quanto tempo essa empresa guarda a imagem ou se a utiliza '
                                   'para treinar modelos. O cliente precisa saber disso antes de '
                                   'decidir.',
                          'destaque': True},
                      {   'titulo': 'Cada cliente decide por si',
                          'texto': 'O consentimento é individual: vale para um cliente, não para '
                                   'a sua carteira. Um cliente que recusou continua com '
                                   'cadastro, histórico e agenda normais — apenas sem '
                                   'simulação.'},
                      {   'titulo': 'Menores de idade',
                          'texto': 'Quando o cliente tem menos de 18 anos, quem consente é um '
                                   'dos pais ou o responsável legal, que precisa estar presente '
                                   'no momento do registro e se identificar.'},
                      {   'titulo': 'Cancelamento é direito do cliente',
                          'texto': 'Se o cliente pedir para cancelar, faça na hora, pelo perfil '
                                   'dele. Cancelar é tão simples quanto aceitar, e você pode '
                                   'apagar as imagens já guardadas no mesmo lugar.'}]}]


def upgrade() -> None:
    conexao = op.get_bind()
    for termo in TERMOS:
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
    """Remove os termos publicados.

    Uma versão já apresentada a alguém não pode simplesmente desaparecer: as chaves
    estrangeiras de `consentimentos` e `ciencias` usam RESTRICT, de propósito. Se houver
    registro apontando para estes textos, a migração falha com uma mensagem explícita, em
    vez de um erro de integridade cru — desfazer exige antes tratar aqueles registros.
    """
    conexao = op.get_bind()
    em_uso = conexao.execute(
        sa.text(
            """
            SELECT t.tipo, t.versao
            FROM termos t
            WHERE EXISTS (SELECT 1 FROM consentimentos c WHERE c.termo_id = t.id)
               OR EXISTS (SELECT 1 FROM ciencias k WHERE k.termo_id = t.id)
            """
        )
    ).all()
    if em_uso:
        referenciados = ", ".join(f"{tipo} v{versao}" for tipo, versao in em_uso)
        raise RuntimeError(
            "não é possível remover termos já apresentados: "
            f"{referenciados}. Apague primeiro os consentimentos e as ciências "
            "correspondentes (por exemplo, excluindo as contas de demonstração)."
        )

    for termo in TERMOS:
        conexao.execute(
            sa.text("DELETE FROM termos WHERE tipo = :tipo AND versao = :versao"),
            {"tipo": termo["tipo"], "versao": termo["versao"]},
        )
