"""Qual modelo atende o pedido, e com quais parâmetros.

É a única parte do sistema que conhece os modelos e os nomes dos campos de cada um. O
aplicativo manda o pedido (texto e marcas de "manter"); o identificador do modelo nunca vem
dele: sai da configuração do servidor.

A regra de escolha, em ordem:

1. **Corte e cor cabem nas opções do modelo principal** (`AI_MODELO`, o
   `change-haircut`) → ele mesmo, com os valores exatos das opções. É o caminho
   especializado e o primeiro a ser tentado.
2. **O modelo principal aceita texto livre nesses campos** (se o schema publicado não tiver
   lista de opções) → ele mesmo, com a descrição.
3. **Descrição livre** que não cabe nas opções → modelo de edição por texto
   (`AI_MODELO_TEXTO`), com instrução montada em `instrucoes.py`.

O gênero do corte (`gender`) só existe no modelo principal e vai a ele nos caminhos 1 e 2,
com o valor escolhido na tela. No caminho 3 o modelo de texto não tem esse campo: o gênero
escolhido vira uma frase da instrução (`instrucoes.py`).

Quando o schema ao vivo não está disponível (provedor local, ou a prévia no aplicativo),
a escolha usa o que o catálogo sabe dos valores das opções. Na geração de verdade, o
schema publicado pela Replicate é consultado e tem a palavra final.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.erros import ValidacaoFalhou
from app.services.ai.base import FalhaDoProvedor
from app.services.ai.esquema import EsquemaModelo
from app.services.ai.instrucoes import Estrategia, descrever, prompt_edicao
from app.services.ai.pedido import GENERO_PADRAO, Alteracao, PedidoCapilar

log = logging.getLogger(__name__)

#: Valor do `change-haircut` para "não mexer" (é o padrão do próprio modelo).
SEM_MUDANCA = "No change"

#: Os dois modelos recebem a foto do cliente neste campo.
CAMPO_IMAGEM = "input_image"

#: Gênero do corte no `change-haircut` ("none", "male" ou "female").
CAMPO_GENERO = "gender"


class Modo(StrEnum):
    #: Modelo principal com valores das opções fechadas.
    opcoes = "opcoes"
    #: Descrição livre (no modelo de edição por texto, ou no principal se ele aceitar).
    descricao = "descricao"


DESCRICAO_DO_MODO = {
    Modo.opcoes: "Troca de corte e cor com as opções do modelo especializado",
    Modo.descricao: "Edição a partir da descrição escrita",
}


@dataclass(frozen=True)
class Plano:
    modo: Modo
    modelo: str
    #: Parâmetros de texto e opções, sem a imagem.
    campos: dict[str, Any]
    #: Campos sem os quais o pedido perde o sentido: se o schema não os tiver, ou não
    #: aceitar o valor, a geração para antes de gastar.
    essenciais: frozenset[str] = field(default_factory=frozenset)

    @property
    def instrucao(self) -> str:
        """O que foi pedido ao modelo, em texto. Fica gravado na simulação."""
        if "prompt" in self.campos:
            return str(self.campos["prompt"])
        # "gender=none" é o padrão do modelo e não aparece: o registro das simulações sem
        # gênero escolhido continua igual ao de antes da opção existir.
        return "; ".join(
            f"{nome}={valor}"
            for nome, valor in self.campos.items()
            if nome in ("haircut", "hair_color")
            or (nome == CAMPO_GENERO and valor != GENERO_PADRAO)
        )


@dataclass(frozen=True)
class Configuracao:
    """O recorte da configuração do servidor que a escolha usa."""

    modelo_principal: str
    modelo_texto: str
    estrategia: Estrategia = "pt_com_termos"


def configuracao_de(config) -> Configuracao:
    return Configuracao(
        modelo_principal=config.ai_modelo,
        modelo_texto=config.ai_modelo_texto,
        estrategia=config.ai_instrucao_idioma,
    )


COMUNS = {"aspect_ratio": "match_input_image", "output_format": "jpg"}


def _valor_nas_opcoes(alteracao: Alteracao, esquema: EsquemaModelo | None, campo: str) -> str | None:
    """O valor da lista de opções que representa a alteração, ou None se não houver."""
    if not alteracao.opcoes_do_modelo:
        return None
    if esquema is None:
        return alteracao.opcoes_do_modelo[0]
    definicao = esquema.campos.get(campo)
    if definicao is None or definicao.opcoes is None:
        return None
    for candidato in alteracao.opcoes_do_modelo:
        exato = definicao.opcao_equivalente(candidato)
        if exato is not None:
            return exato
    log.warning(
        "nome do catálogo sem equivalente nas opções publicadas: campo=%s candidatos=%s",
        campo,
        list(alteracao.opcoes_do_modelo),
    )
    return None


def _sem_mudanca(esquema: EsquemaModelo | None, campo: str) -> str | None:
    if esquema is None:
        return SEM_MUDANCA
    definicao = esquema.campos.get(campo)
    if definicao is None:
        return None
    if definicao.opcoes is None:
        return SEM_MUDANCA
    return definicao.opcao_equivalente(SEM_MUDANCA)


def _principal_aceita_texto(esquema: EsquemaModelo | None, pedido: PedidoCapilar) -> bool:
    """O schema publicado do modelo principal recebe texto livre onde o pedido precisa?"""
    if esquema is None:
        return False
    for alteracao, campo in ((pedido.corte, "haircut"), (pedido.cor, "hair_color")):
        if alteracao is None:
            continue
        definicao = esquema.campos.get(campo)
        if definicao is None or definicao.opcoes is not None or definicao.tipo != "string":
            return False
    return True


def _genero_essencial(pedido: PedidoCapilar) -> set[str]:
    """Gênero escolhido na tela não pode sumir do envio: se o modelo deixar de aceitá-lo,
    a geração para antes de gastar. "none" é o padrão do modelo e pode ficar de fora."""
    return {CAMPO_GENERO} if pedido.genero != GENERO_PADRAO else set()


def planejar(
    pedido: PedidoCapilar,
    config: Configuracao,
    esquema_principal: EsquemaModelo | None = None,
) -> Plano:
    # 1. Opções fechadas do modelo principal.
    valores: dict[str, str] = {}
    cabe_nas_opcoes = True
    for alteracao, campo in ((pedido.corte, "haircut"), (pedido.cor, "hair_color")):
        if alteracao is None:
            neutro = _sem_mudanca(esquema_principal, campo)
            if neutro is not None:
                valores[campo] = neutro
            continue
        valor = _valor_nas_opcoes(alteracao, esquema_principal, campo)
        if valor is None:
            cabe_nas_opcoes = False
            break
        valores[campo] = valor
    if cabe_nas_opcoes:
        return Plano(
            modo=Modo.opcoes,
            modelo=config.modelo_principal,
            campos={**valores, CAMPO_GENERO: pedido.genero, **COMUNS},
            essenciais=frozenset(
                {CAMPO_IMAGEM}
                | ({"haircut"} if pedido.corte is not None else set())
                | ({"hair_color"} if pedido.cor is not None else set())
                | _genero_essencial(pedido)
            ),
        )

    # 2. O modelo principal aceita texto livre nesses campos.
    if _principal_aceita_texto(esquema_principal, pedido):
        campos: dict[str, str] = {}
        for alteracao, campo in ((pedido.corte, "haircut"), (pedido.cor, "hair_color")):
            if alteracao is not None:
                campos[campo] = descrever(alteracao, config.estrategia)
            else:
                neutro = _sem_mudanca(esquema_principal, campo)
                if neutro is not None:
                    campos[campo] = neutro
        return Plano(
            modo=Modo.descricao,
            modelo=config.modelo_principal,
            campos={**campos, CAMPO_GENERO: pedido.genero, **COMUNS},
            essenciais=frozenset(
                {CAMPO_IMAGEM, *(c for c in ("haircut", "hair_color") if c in campos)}
                | _genero_essencial(pedido)
            ),
        )

    # 3. Modelo de edição por texto.
    if not config.modelo_texto:
        raise ValidacaoFalhou(
            "A descrição livre está desligada neste servidor (AI_MODELO_TEXTO vazio). "
            "Use exatamente um dos exemplos da tela, ou peça para ligar a descrição livre.",
            codigo="descricao_livre_indisponivel",
        )
    return Plano(
        modo=Modo.descricao,
        modelo=config.modelo_texto,
        campos={"prompt": prompt_edicao(pedido, config.estrategia), **COMUNS},
        essenciais=frozenset({"prompt", CAMPO_IMAGEM}),
    )


def montar_entrada(plano: Plano, imagem: str, esquema: EsquemaModelo | None) -> dict[str, Any]:
    """Junta a imagem e os parâmetros e confere tudo contra o schema publicado do modelo.

    Campo que o modelo não tem: se for essencial, a geração para (`modelo_incompativel`);
    se for acessório (proporção, formato), sai do envio e o modelo usa o padrão dele.
    Valor fora das opções: mesma regra (`parametro_fora_do_schema`). Sem schema (provedor
    local), segue como está.
    """
    entrada: dict[str, Any] = {CAMPO_IMAGEM: imagem, **plano.campos}
    if esquema is None:
        return entrada

    for nome in list(entrada):
        definicao = esquema.campos.get(nome)
        if definicao is None:
            if nome in plano.essenciais:
                raise FalhaDoProvedor(
                    f"O modelo {plano.modelo} não tem o campo '{nome}' no schema publicado.",
                    codigo="modelo_incompativel",
                )
            log.info("campo %s fora do schema de %s: não enviado", nome, plano.modelo)
            del entrada[nome]
            continue
        if not definicao.aceita(entrada[nome]):
            if nome in plano.essenciais:
                raise FalhaDoProvedor(
                    f"O valor de '{nome}' não está entre as opções publicadas de {plano.modelo}.",
                    codigo="parametro_fora_do_schema",
                )
            log.info("valor de %s fora das opções de %s: não enviado", nome, plano.modelo)
            del entrada[nome]

    faltando = [nome for nome in esquema.obrigatorios if nome not in entrada]
    if faltando:
        raise FalhaDoProvedor(
            f"O modelo {plano.modelo} exige campos que o sistema não envia: {', '.join(faltando)}.",
            codigo="modelo_incompativel",
        )
    return entrada
