"""Carga de desenvolvimento (seção 34 da especificação).

Reproduz no PostgreSQL os mesmos cenários que o protótipo tinha em `src/data/seed.ts`,
para que os cinco estados de consentimento possam ser demonstrados sem preparar dados à
mão. **Todos os dados são fictícios.**

Cenários:

| cliente        | situação                                      |
| -------------- | --------------------------------------------- |
| Aline Barros   | aceito na versão vigente (câmera liberada)    |
| Bruno Tavares  | nenhuma decisão registrada (pendente)         |
| Carla Menezes  | recusou (câmera bloqueada)                    |
| Júlia Stein    | aceitou a versão 0.9 (exige revalidação)      |
| Marina Alves   | aceito, com três simulações e uma preferida   |
| Rafael Prado   | aceitou e depois revogou (dois registros)     |
| Sofia Ramires  | 16 anos, aceite dado pela mãe                 |

Além da carteira do profissional de demonstração, cria um **segundo** profissional com
clientes próprios: é o que permite demonstrar e testar o isolamento entre contas.

Uso:
    python -m app.seed            # cria se ainda não existir
    python -m app.seed --reset    # apaga os usuários de demonstração e recria
"""

from __future__ import annotations

import argparse
import io
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.security import gerar_hash_senha
from app.db.session import FabricaSessao
from app.models import (
    Agendamento,
    Atendimento,
    Ciencia,
    Cliente,
    Consentimento,
    DecisaoConsentimento,
    FormaObtencao,
    Imagem,
    Simulacao,
    StatusAgendamento,
    StatusSimulacao,
    Termo,
    TipoImagem,
    TipoTermo,
    Usuario,
)
from app.services.regras_consentimento import faixa_etaria
from app.services.storage import montar_chave, obter_armazenamento, prefixo_do_usuario

SENHA_DEMO = "espelho-demo-2026"

EMAIL_PRINCIPAL = "carolina@salaoexemplo.com.br"
EMAIL_SECUNDARIO = "diego@salaoexemplo.com.br"


# --- Apoio ----------------------------------------------------------------


def em_relacao_a_hoje(dias: int, hora: int = 12, minuto: int = 0) -> datetime:
    """Dia e hora no fuso do salão: "14h30" da demonstração é 14h30 em Brasília."""
    base = datetime.now(obter_config().fuso) + timedelta(days=dias)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def nascido_ha(anos: int) -> date:
    hoje = date.today()
    return date(hoje.year - anos, 4, 12)


def retrato_sintetico(semente: int, tom: tuple[int, int, int]) -> bytes:
    """Imagem de demonstração em formato retrato.

    Não é fotografia de pessoa alguma: é um gráfico gerado aqui mesmo, para que as telas
    de resultado e de comparação tenham o que exibir sem usar imagem real de ninguém.
    """
    largura, altura = 720, 960
    imagem = Image.new("RGB", (largura, altura), (248, 244, 240))
    desenho = ImageDraw.Draw(imagem)
    for y in range(altura):
        mistura = y / altura
        desenho.line(
            [(0, y), (largura, y)],
            fill=(
                int(248 - mistura * 60),
                int(244 - mistura * 70),
                int(240 - mistura * 80),
            ),
        )
    desenho.ellipse([180, 170, 540, 650], fill=tom)
    desenho.ellipse([150, 120, 570, 420], fill=tuple(max(0, c - 40) for c in tom))
    desenho.text((40, altura - 60), f"amostra {semente}", fill=(90, 80, 72))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


@dataclass
class Resumo:
    usuarios: int = 0
    clientes: int = 0
    consentimentos: int = 0
    simulacoes: int = 0
    atendimentos: int = 0
    agendamentos: int = 0
    imagens: int = 0

    def __str__(self) -> str:
        return (
            f"{self.usuarios} usuários · {self.clientes} clientes · "
            f"{self.consentimentos} consentimentos · {self.simulacoes} simulações · "
            f"{self.imagens} imagens · {self.atendimentos} atendimentos · "
            f"{self.agendamentos} agendamentos"
        )


def _termo_vigente(sessao: Session, tipo: TipoTermo) -> Termo:
    termo = sessao.scalar(select(Termo).where(Termo.tipo == tipo, Termo.vigente.is_(True)))
    if termo is None:
        raise RuntimeError(
            f"nenhum termo vigente do tipo {tipo.value}: rode `alembic upgrade head` antes do seed"
        )
    return termo


def _termo_por_versao(sessao: Session, tipo: TipoTermo, versao: str) -> Termo:
    termo = sessao.scalar(select(Termo).where(Termo.tipo == tipo, Termo.versao == versao))
    if termo is None:
        raise RuntimeError(f"termo {tipo.value} v{versao} não encontrado")
    return termo


# --- Carga ----------------------------------------------------------------


def limpar(sessao: Session) -> None:
    """Remove os usuários de demonstração e, em cascata, tudo o que é deles."""
    armazenamento = obter_armazenamento()
    usuarios = list(
        sessao.scalars(
            select(Usuario).where(Usuario.email.in_([EMAIL_PRINCIPAL, EMAIL_SECUNDARIO]))
        )
    )
    for usuario in usuarios:
        armazenamento.excluir_prefixo(prefixo_do_usuario(usuario.id))
        sessao.delete(usuario)
    sessao.commit()


def popular(sessao: Session) -> Resumo:
    resumo = Resumo()
    armazenamento = obter_armazenamento()

    termo_cliente = _termo_vigente(sessao, TipoTermo.cliente)
    termo_antigo = _termo_por_versao(sessao, TipoTermo.cliente, "0.9")
    aviso = _termo_vigente(sessao, TipoTermo.profissional)

    profissional = Usuario(
        nome="Carolina Dutra",
        email=EMAIL_PRINCIPAL,
        senha_hash=gerar_hash_senha(SENHA_DEMO),
        atuacao="autônomo",
    )
    colega = Usuario(
        nome="Diego Matos",
        email=EMAIL_SECUNDARIO,
        senha_hash=gerar_hash_senha(SENHA_DEMO),
        atuacao="salão",
    )
    sessao.add_all([profissional, colega])
    sessao.flush()
    resumo.usuarios = 2

    sessao.add(
        Ciencia(
            usuario_id=profissional.id,
            termo_id=aviso.id,
            versao=aviso.versao,
            registrada_em=em_relacao_a_hoje(-300, 9, 10),
        )
    )

    def novo_cliente(
        usuario: Usuario,
        nome: str,
        telefone: str,
        observacoes: str,
        dias: int,
        nascimento: date | None = None,
    ) -> Cliente:
        cliente = Cliente(
            usuario_id=usuario.id,
            nome=nome,
            telefone=telefone,
            observacoes=observacoes,
            data_nascimento=nascimento,
            criado_em=em_relacao_a_hoje(-dias),
        )
        sessao.add(cliente)
        resumo.clientes += 1
        return cliente

    aline = novo_cliente(
        profissional,
        "Aline Barros",
        "(55) 99812-3320",
        "Fios finos, evita volume no topo. Gosta de manutenção a cada seis semanas.",
        300,
    )
    bruno = novo_cliente(
        profissional, "Bruno Tavares", "(55) 99655-1180", "Corte na máquina 2 nas laterais.", 260
    )
    carla = novo_cliente(
        profissional,
        "Carla Menezes",
        "(55) 99744-2091",
        "Couro cabeludo sensível. Usar coloração sem amônia.",
        210,
    )
    julia = novo_cliente(
        profissional,
        "Júlia Stein",
        "(55) 99333-7712",
        "Quer clarear aos poucos. Já teve quebra por descoloração em 2024.",
        180,
    )
    marina = novo_cliente(
        profissional,
        "Marina Alves",
        "(55) 99123-4567",
        "Histórico de descoloração. Prefere tons quentes. Sensível a amônia.",
        620,
    )
    rafael = novo_cliente(
        profissional, "Rafael Prado", "(55) 99480-6654", "Barba aparada junto com o corte.", 140
    )
    sofia = novo_cliente(
        profissional,
        "Sofia Ramires",
        "(55) 99271-8845",
        "Cacheada, rotina de hidratação quinzenal. Vem sempre com a mãe.",
        95,
        nascido_ha(16),
    )

    # Carteira do segundo profissional: serve para demonstrar o isolamento entre contas.
    novo_cliente(colega, "Helena Prado", "(55) 99101-2020", "Cliente de outro profissional.", 80)
    novo_cliente(colega, "Igor Bastos", "(55) 99102-3030", "Cliente de outro profissional.", 50)

    sessao.flush()

    def registrar(
        cliente: Cliente,
        decisao: DecisaoConsentimento,
        termo: Termo,
        dias: int,
        hora: int,
        minuto: int,
        forma: FormaObtencao,
        confirmado_por: str,
        observacao: str = "",
        responsavel: tuple[str, str] | None = None,
    ) -> Consentimento:
        registro = Consentimento(
            cliente_id=cliente.id,
            usuario_id=profissional.id,
            decisao=decisao,
            termo_id=termo.id,
            versao_termo=termo.versao,
            registrado_em=em_relacao_a_hoje(dias, hora, minuto),
            forma_obtencao=forma,
            confirmado_por=confirmado_por,
            responsavel_nome=responsavel[0] if responsavel else None,
            responsavel_parentesco=responsavel[1] if responsavel else None,
            faixa_etaria=faixa_etaria(cliente.data_nascimento),
            observacao=observacao,
        )
        sessao.add(registro)
        resumo.consentimentos += 1
        return registro

    k_aline = registrar(
        aline,
        DecisaoConsentimento.aceito,
        termo_cliente,
        -30,
        10,
        12,
        FormaObtencao.tela_dispositivo,
        "Aline Barros",
    )
    registrar(
        carla,
        DecisaoConsentimento.recusado,
        termo_cliente,
        -26,
        16,
        40,
        FormaObtencao.lido_em_voz_alta,
        "Carla Menezes",
        "Preferiu não ter a foto enviada a outra empresa.",
    )
    k_julia = registrar(
        julia,
        DecisaoConsentimento.aceito,
        termo_antigo,
        -120,
        9,
        5,
        FormaObtencao.tela_dispositivo,
        "Júlia Stein",
    )
    k_marina = registrar(
        marina,
        DecisaoConsentimento.aceito,
        termo_cliente,
        -70,
        14,
        20,
        FormaObtencao.tela_dispositivo,
        "Marina Alves",
    )
    registrar(
        rafael,
        DecisaoConsentimento.aceito,
        termo_cliente,
        -60,
        17,
        30,
        FormaObtencao.tela_dispositivo,
        "Rafael Prado",
    )
    registrar(
        rafael,
        DecisaoConsentimento.revogado,
        termo_cliente,
        -12,
        11,
        15,
        FormaObtencao.lido_em_voz_alta,
        "Rafael Prado",
        "Pediu o cancelamento por telefone e confirmou na visita seguinte.",
    )
    registrar(
        sofia,
        DecisaoConsentimento.aceito,
        termo_cliente,
        -40,
        15,
        0,
        FormaObtencao.tela_dispositivo,
        "Denise Ramires",
        "Responsável presente no atendimento.",
        responsavel=("Denise Ramires", "Mãe"),
    )
    # Bruno permanece sem registro: é o cenário `pendente`.
    sessao.flush()

    def nova_imagem(
        cliente: Cliente, tipo: TipoImagem, simulacao_id: uuid.UUID, semente: int, tom: tuple[int, int, int]
    ) -> Imagem:
        conteudo = retrato_sintetico(semente, tom)
        chave = montar_chave(profissional.id, cliente.id, tipo, "image/jpeg", simulacao_id)
        armazenamento.salvar(chave, conteudo, "image/jpeg")
        imagem = Imagem(
            usuario_id=profissional.id,
            cliente_id=cliente.id,
            tipo=tipo,
            chave_objeto=chave,
            mime="image/jpeg",
            bytes=len(conteudo),
            largura=720,
            altura=960,
        )
        sessao.add(imagem)
        resumo.imagens += 1
        return imagem

    def nova_simulacao(
        cliente: Cliente,
        consentimento: Consentimento,
        estilo: str,
        cor: str,
        observacoes: str,
        tempo_ms: int,
        dias: int,
        hora: int,
        minuto: int,
        tom: tuple[int, int, int],
        preferida: bool = False,
    ) -> Simulacao:
        identificador = uuid.uuid4()
        entrada = nova_imagem(cliente, TipoImagem.entrada, identificador, resumo.imagens + 1, (74, 50, 42))
        saida = nova_imagem(cliente, TipoImagem.saida, identificador, resumo.imagens + 1, tom)
        sessao.flush()
        criado = em_relacao_a_hoje(dias, hora, minuto)
        simulacao = Simulacao(
            id=identificador,
            cliente_id=cliente.id,
            usuario_id=profissional.id,
            consentimento_id=consentimento.id,
            img_entrada_id=entrada.id,
            img_saida_id=saida.id,
            estilo=estilo,
            cor=cor,
            observacoes=observacoes,
            status=StatusSimulacao.concluida,
            provedor="demonstracao",
            modelo_ia="dados de demonstração",
            tempo_ms=tempo_ms,
            preferida=preferida,
            criado_em=criado,
            concluida_em=criado,
        )
        sessao.add(simulacao)
        resumo.simulacoes += 1
        return simulacao

    sim_marina = nova_simulacao(
        marina,
        k_marina,
        "Médio em camadas",
        "Castanho acobreado",
        "Manter comprimento nos ombros, testar antes de decidir a cor.",
        14000,
        -10,
        14,
        52,
        (162, 90, 52),
        preferida=True,
    )
    nova_simulacao(
        marina, k_marina, "Bob curto", "Loiro mel", "", 19000, -23, 10, 30, (199, 154, 91)
    )
    nova_simulacao(
        marina,
        k_marina,
        "Longo liso",
        "Platinado",
        "Cliente quis ver o extremo.",
        21000,
        -67,
        16,
        5,
        (216, 210, 200),
    )
    sim_aline = nova_simulacao(
        aline, k_aline, "Curto texturizado", "Castanho escuro", "", 12000, -8, 11, 20, (74, 50, 42)
    )
    nova_simulacao(
        julia, k_julia, "Franja cortina", "Loiro mel", "", 17000, -4, 9, 45, (199, 154, 91)
    )
    sessao.flush()

    def novo_atendimento(
        cliente: Cliente,
        simulacao: Simulacao | None,
        descricao: str,
        dias: int,
        observacoes: str,
    ) -> None:
        sessao.add(
            Atendimento(
                cliente_id=cliente.id,
                usuario_id=profissional.id,
                simulacao_id=simulacao.id if simulacao else None,
                descricao=descricao,
                data_servico=(datetime.now(obter_config().fuso) + timedelta(days=dias)).date(),
                observacoes=observacoes,
            )
        )
        resumo.atendimentos += 1

    novo_atendimento(
        marina,
        sim_marina,
        "Coloração acobreada + corte médio",
        -10,
        "Aprovou a simulação de tom acobreado. Executado com 2 tons abaixo do simulado por "
        "causa do histórico de descoloração.",
    )
    novo_atendimento(
        marina,
        None,
        "Hidratação",
        -23,
        "Sem simulação. Cliente pediu para ver opções de corte curto na próxima visita.",
    )
    novo_atendimento(aline, sim_aline, "Corte curto texturizado", -8, "Seguiu a simulação sem ajustes.")
    novo_atendimento(carla, None, "Coloração sem amônia", -21, "Sem reação no couro cabeludo.")

    def novo_agendamento(
        cliente: Cliente,
        dias: int,
        hora: int,
        minuto: int,
        servico: str,
        status: StatusAgendamento,
        duracao: int | None,
        lembrete: bool,
        observacoes: str = "",
    ) -> Agendamento:
        agendamento = Agendamento(
            cliente_id=cliente.id,
            usuario_id=profissional.id,
            data_hora=em_relacao_a_hoje(dias, hora, minuto),
            servico=servico,
            duracao_min=duracao,
            status=status,
            observacoes=observacoes,
            lembrete=lembrete,
        )
        sessao.add(agendamento)
        resumo.agendamentos += 1
        return agendamento

    novo_agendamento(
        marina,
        0,
        14,
        30,
        "Coloração + corte",
        StatusAgendamento.confirmado,
        120,
        True,
        "Retomar a simulação acobreada aprovada.",
    )
    novo_agendamento(rafael, 0, 16, 0, "Corte masculino", StatusAgendamento.pendente, 45, True)
    novo_agendamento(
        julia, 0, 18, 15, "Avaliação de coloração", StatusAgendamento.confirmado, 30, False
    )
    novo_agendamento(aline, 3, 10, 0, "Retoque de cor", StatusAgendamento.confirmado, 90, True)
    novo_agendamento(sofia, 5, 15, 0, "Hidratação", StatusAgendamento.pendente, 60, True)
    novo_agendamento(carla, 9, 13, 30, "Coloração", StatusAgendamento.confirmado, 120, True)
    # Serviço fora da lista ("Outro") e sem duração prevista: a duração é opcional.
    novo_agendamento(
        julia, 6, 17, 0, "Penteado para festa", StatusAgendamento.pendente, None, False,
        "Casamento da irmã no sábado.",
    )
    # Um compromisso concluído pelo fluxo da agenda: gera o atendimento ligado a ele, com
    # o horário real (aqui, 20 minutos depois do marcado) separado do horário previsto.
    concluido = novo_agendamento(
        bruno, -4, 17, 0, "Corte masculino", StatusAgendamento.concluido, 45, False
    )
    sessao.flush()
    realizado = concluido.data_hora + timedelta(minutes=20)
    sessao.add(
        Atendimento(
            cliente_id=bruno.id,
            usuario_id=profissional.id,
            agendamento_id=concluido.id,
            descricao="Corte masculino",
            data_servico=realizado.astimezone(obter_config().fuso).date(),
            realizado_em=realizado,
            observacoes="Começou 20 minutos depois do horário marcado.",
        )
    )
    resumo.atendimentos += 1

    # Um cancelamento: continua visível na agenda, com o motivo, e não ocupa o horário.
    cancelado = novo_agendamento(sofia, 2, 11, 0, "Escova", StatusAgendamento.cancelado, 60, False)
    cancelado.cancelado_em = datetime.now(UTC)
    cancelado.motivo_cancelamento = "Cliente pediu para remarcar."

    sessao.commit()
    return resumo


def main() -> int:
    analisador = argparse.ArgumentParser(description="Popula o banco com dados de demonstração.")
    analisador.add_argument(
        "--reset", action="store_true", help="apaga os usuários de demonstração antes de recriar"
    )
    argumentos = analisador.parse_args()

    # As contas de demonstração têm senha publicada na documentação. Em produção elas
    # seriam contas abertas a qualquer um; o seed se recusa, mesmo que alguém esqueça
    # `SEED_AO_SUBIR=true` no ambiente.
    if obter_config().producao:
        print("Dados de demonstração não são criados com AMBIENTE=producao.", file=sys.stderr)
        return 2

    with FabricaSessao() as sessao:
        if argumentos.reset:
            limpar(sessao)
        existente = sessao.scalar(select(Usuario).where(Usuario.email == EMAIL_PRINCIPAL))
        if existente is not None:
            print(
                "Os dados de demonstração já existem. Use --reset para recriar.",
                file=sys.stderr,
            )
            return 1
        resumo = popular(sessao)

    print(f"Seed concluído: {resumo}")
    print(f"Entre com {EMAIL_PRINCIPAL} / {SENHA_DEMO}")
    print(f"Segunda conta (isolamento): {EMAIL_SECUNDARIO} / {SENHA_DEMO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
