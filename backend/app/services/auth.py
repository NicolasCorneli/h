"""Cadastro, autenticação, renovação, ciência e exclusão de conta (RF01)."""

from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.erros import Conflito, NaoAutenticado, NaoEncontrado, SemPermissao, ValidacaoFalhou
from app.core.security import (
    TokenInvalido,
    criar_token,
    gerar_hash_senha,
    ler_dados_do_token,
    verificar_senha,
)
from app.models import Ciencia, IdentidadeExterna, TipoTermo, Usuario
from app.repositories import consultas
from app.schemas.auth import CienciaOut, Registro, SessaoOut, TokensOut, UsuarioOut
from app.services import google
from app.services.storage import obter_armazenamento, prefixo_do_usuario

log = logging.getLogger(__name__)

#: Hash descartável usado quando o e-mail não existe, para que a resposta demore o mesmo
#: tanto com e sem usuário — um login mais rápido revelaria que o e-mail não está cadastrado.
_HASH_REFERENCIA = gerar_hash_senha("referencia-sem-usuario")


def usuario_out(usuario: Usuario) -> UsuarioOut:
    """Dados da conta para o aplicativo, com a URL assinada da foto, quando houver."""
    from sqlalchemy.orm import object_session

    from app.services.imagens import uri_assinada

    sessao = object_session(usuario)
    foto = consultas.foto_do_usuario(sessao, usuario.id) if sessao is not None else None
    saida = UsuarioOut.model_validate(usuario)
    saida.foto_uri = uri_assinada(foto, usuario.id)
    return saida


def _sessao_para(usuario: Usuario) -> SessaoOut:
    config = obter_config()
    return SessaoOut(
        tokens=TokensOut(
            access_token=criar_token(usuario.id, "access", usuario.versao_sessao),
            refresh_token=criar_token(usuario.id, "refresh", usuario.versao_sessao),
            expira_em=config.jwt_minutos_access * 60,
        ),
        usuario=usuario_out(usuario),
    )


def registrar(sessao: Session, dados: Registro) -> SessaoOut:
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email.strip().lower(),
        senha_hash=gerar_hash_senha(dados.senha),
        atuacao=dados.atuacao or "autônomo",
    )
    sessao.add(usuario)
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise Conflito("Já existe uma conta com este e-mail.", codigo="email_em_uso") from None
    sessao.refresh(usuario)
    return _sessao_para(usuario)


def autenticar(sessao: Session, email: str, senha: str) -> SessaoOut:
    usuario = consultas.usuario_por_email(sessao, email)
    # Mesma mensagem para e-mail inexistente e senha errada: não revela se o e-mail
    # está cadastrado. A verificação roda mesmo sem usuário para não vazar pelo tempo.
    # Conta sem senha (criada pelo Google) cai no mesmo caminho de senha errada.
    hash_referencia = usuario.senha_hash if usuario and usuario.senha_hash else _HASH_REFERENCIA
    senha_correta = verificar_senha(senha, hash_referencia)
    if usuario is None or not usuario.senha_hash or not senha_correta or not usuario.ativo:
        raise NaoAutenticado("E-mail ou senha incorretos.", codigo="credenciais_invalidas")
    return _sessao_para(usuario)


def renovar(sessao: Session, refresh_token: str) -> TokensOut:
    try:
        dados = ler_dados_do_token(refresh_token, "refresh")
    except TokenInvalido:
        raise NaoAutenticado("Faça login novamente.", codigo="refresh_invalido") from None

    usuario = sessao.get(Usuario, dados.usuario_id)
    if usuario is None or not usuario.ativo:
        raise NaoAutenticado("Conta não encontrada.", codigo="refresh_invalido")
    if dados.versao_sessao != usuario.versao_sessao:
        # Um token de renovação copiado deixa de valer quando a senha muda ou quando a
        # dona da conta encerra as sessões. Antes, valia até expirar (30 dias).
        raise NaoAutenticado("Faça login novamente.", codigo="refresh_invalido")
    return _sessao_para(usuario).tokens


# --- Senha e sessões --------------------------------------------------------


def _encerrar_sessoes(sessao: Session, usuario: Usuario) -> None:
    """Invalida todo token já emitido para a conta, em todos os aparelhos.

    O incremento é feito no banco (`versao_sessao + 1`), e não a partir do valor em
    memória: duas chamadas simultâneas incrementam duas vezes, em vez de gravarem o
    mesmo número e deixarem uma delas sem efeito.
    """
    sessao.execute(
        update(Usuario)
        .where(Usuario.id == usuario.id)
        .values(versao_sessao=Usuario.versao_sessao + 1)
    )


def trocar_senha(sessao: Session, usuario: Usuario, senha_atual: str, nova_senha: str) -> SessaoOut:
    """Troca a senha e encerra as outras sessões; devolve uma sessão nova para este aparelho.

    Pede a senha atual: um token de acesso roubado não basta para tomar a conta.
    """
    if usuario.senha_hash is None:
        raise ValidacaoFalhou(
            "Esta conta entra pelo Google e não tem senha para trocar.",
            codigo="conta_sem_senha",
        )
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise SemPermissao("Senha atual incorreta.", codigo="senha_incorreta")
    if senha_atual == nova_senha:
        raise ValidacaoFalhou(
            "A nova senha precisa ser diferente da atual.",
            codigo="senha_repetida",
            detalhes=[{"campo": "novaSenha"}],
        )
    usuario.senha_hash = gerar_hash_senha(nova_senha)
    _encerrar_sessoes(sessao, usuario)
    sessao.commit()
    sessao.refresh(usuario)
    log.info("senha trocada e sessões encerradas: usuario=%s", usuario.id)
    return _sessao_para(usuario)


def encerrar_todas_as_sessoes(sessao: Session, usuario: Usuario) -> None:
    """"Sair de todos os aparelhos": inclusive deste, que volta para o login."""
    _encerrar_sessoes(sessao, usuario)
    sessao.commit()
    log.info("sessões encerradas a pedido: usuario=%s", usuario.id)


# --- Entrar com Google ----------------------------------------------------

PROVEDOR_GOOGLE = "google"


def _identidade_google(sessao: Session, sujeito: str) -> IdentidadeExterna | None:
    return sessao.scalar(
        select(IdentidadeExterna).where(
            IdentidadeExterna.provedor == PROVEDOR_GOOGLE, IdentidadeExterna.sujeito == sujeito
        )
    )


def entrar_com_google(sessao: Session, token: str, nonce: str | None = None) -> SessaoOut:
    """Login e cadastro pelo Google, num passo só.

    1. A conta Google já está ligada a uma conta daqui: entra nela. A busca é pelo `sub`,
       nunca pelo e-mail.
    2. Não está, mas já existe conta daqui com o mesmo e-mail: recusa, sem ligar nada. As
       contas por senha não confirmam o e-mail no cadastro; ligar só porque o e-mail
       coincide entregaria a conta a quem a criou com o e-mail de outra pessoa (ou o
       contrário). A dona da conta liga o Google pelo Perfil, depois de entrar com a senha.
    3. Nenhuma das duas: cria a conta, sem senha, já ligada ao Google.
    """
    identidade = google.verificar_id_token(token, nonce)

    existente = _identidade_google(sessao, identidade.sujeito)
    if existente is not None:
        usuario = existente.usuario
        if not usuario.ativo:
            raise NaoAutenticado("Conta não encontrada.", codigo="credenciais_invalidas")
        return _sessao_para(usuario)

    if consultas.usuario_por_email(sessao, identidade.email) is not None:
        raise Conflito(
            "Já existe uma conta com este e-mail. Entre com e-mail e senha e, no Perfil, "
            "conecte sua conta Google.",
            codigo="google_email_em_uso",
        )

    nome = identidade.nome if len(identidade.nome) >= 2 else identidade.email.split("@")[0]
    usuario = Usuario(nome=nome, email=identidade.email, senha_hash=None)
    usuario.identidades.append(
        IdentidadeExterna(
            provedor=PROVEDOR_GOOGLE, sujeito=identidade.sujeito, email=identidade.email
        )
    )
    sessao.add(usuario)
    try:
        sessao.commit()
    except IntegrityError:
        # Duas tentativas simultâneas com a mesma conta Google, ou um cadastro por senha
        # com o mesmo e-mail no mesmo instante.
        sessao.rollback()
        raise Conflito(
            "Não foi possível concluir o cadastro agora. Tente entrar de novo.",
            codigo="google_conflito",
        ) from None
    sessao.refresh(usuario)
    log.info("conta criada pelo Google: usuario=%s", usuario.id)
    return _sessao_para(usuario)


def vincular_google(
    sessao: Session, usuario: Usuario, token: str, nonce: str | None = None
) -> Usuario:
    """Liga uma conta Google à conta de quem já entrou.

    Estar autenticado é a prova de que a conta é sua; o token prova que a conta Google
    também é. O e-mail das duas não precisa coincidir.
    """
    identidade = google.verificar_id_token(token, nonce)
    existente = _identidade_google(sessao, identidade.sujeito)
    if existente is not None:
        if existente.usuario_id == usuario.id:
            return usuario
        raise Conflito(
            "Esta conta Google já está ligada a outra conta do aplicativo.",
            codigo="google_ja_vinculado",
        )
    if usuario.google_vinculado:
        raise Conflito(
            "Sua conta já está conectada a outra conta Google. Desconecte-a antes.",
            codigo="google_outra_conta",
        )
    sessao.add(
        IdentidadeExterna(
            usuario_id=usuario.id,
            provedor=PROVEDOR_GOOGLE,
            sujeito=identidade.sujeito,
            email=identidade.email,
        )
    )
    try:
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise Conflito(
            "Esta conta Google já está ligada a outra conta do aplicativo.",
            codigo="google_ja_vinculado",
        ) from None
    sessao.refresh(usuario)
    return usuario


def desvincular_google(sessao: Session, usuario: Usuario) -> Usuario:
    if not usuario.tem_senha:
        # Sem senha, desligar o Google trancaria a pessoa fora da própria conta.
        raise ValidacaoFalhou(
            "Esta conta entra só pelo Google. Desconectar deixaria a conta sem forma de entrar.",
            codigo="google_unica_forma_de_entrar",
        )
    for identidade in list(usuario.identidades):
        if identidade.provedor == PROVEDOR_GOOGLE:
            sessao.delete(identidade)
    sessao.commit()
    sessao.refresh(usuario)
    return usuario


# --- Ciência das responsabilidades ---------------------------------------


def ciencia_atual(sessao: Session, usuario: Usuario) -> CienciaOut:
    registro = consultas.ultima_ciencia(sessao, usuario.id)
    vigente = consultas.termo_vigente(sessao, TipoTermo.profissional)
    versao_vigente = vigente.versao if vigente else None
    # Uma ciência dada sobre um aviso anterior não vale como atual: o profissional
    # precisa reconhecer o texto em vigor.
    aceita = registro is not None and registro.versao == versao_vigente
    return CienciaOut(
        aceita=aceita,
        versao=registro.versao if registro else None,
        registrada_em=registro.registrada_em if registro else None,
    )


def registrar_ciencia(sessao: Session, usuario: Usuario) -> CienciaOut:
    termo = consultas.termo_vigente(sessao, TipoTermo.profissional)
    if termo is None:
        raise NaoEncontrado("Nenhum aviso de responsabilidades publicado.")
    sessao.add(Ciencia(usuario_id=usuario.id, termo_id=termo.id, versao=termo.versao))
    sessao.commit()
    return ciencia_atual(sessao, usuario)


# --- Exclusão de conta ----------------------------------------------------


def excluir_conta(
    sessao: Session, usuario: Usuario, senha: str | None, id_token_google: str | None = None
) -> None:
    """Exclusão física (decisão registrada no diagnóstico §4.10).

    Os objetos do storage saem primeiro: se a transação falhar depois, o pior caso é um
    arquivo já removido de uma conta que continua — detectável e sem dado vazado. A ordem
    inversa deixaria imagens órfãs sem nenhum registro que as encontre.
    """
    if usuario.senha_hash is not None:
        if not senha or not verificar_senha(senha, usuario.senha_hash):
            raise SemPermissao("Senha incorreta.", codigo="senha_incorreta")
    else:
        # Conta sem senha: a confirmação é entrar de novo no Google, com a mesma conta.
        if not id_token_google:
            raise SemPermissao(
                "Confirme com sua conta Google para excluir.", codigo="confirmacao_google"
            )
        identidade = google.verificar_id_token(id_token_google)
        if not any(
            i.provedor == PROVEDOR_GOOGLE and i.sujeito == identidade.sujeito
            for i in usuario.identidades
        ):
            raise SemPermissao(
                "Use a mesma conta Google ligada a esta conta.", codigo="confirmacao_google"
            )

    from app.services.imagens import travar_cliente_para_excluir

    travar_cliente_para_excluir(sessao, usuario_id=usuario.id)
    apagados = obter_armazenamento().excluir_prefixo(prefixo_do_usuario(usuario.id))
    sessao.delete(usuario)
    sessao.commit()
    log.info("conta excluída: usuario=%s objetos_removidos=%s", usuario.id, apagados)
