"""Qual modelo atende o pedido, e com quais parâmetros.

É a única parte do sistema que conhece os modelos e os nomes dos campos de cada um. O
aplicativo manda o pedido (texto e marcas de "manter"); o identificador do modelo nunca vem
dele: sai da configuração do servidor.

Há dois caminhos, escolhidos por `AI_ESTRATEGIA` (em `Configuracao.caminho`):

**`instrucao`**: todo pedido, inclusive os exemplos do catálogo, vai ao modelo de edição por
instrução (`AI_MODELO_TEXTO`, o `google/nano-banana-2.1`), com a instrução detalhada de
`instrucoes.py`. O `AI_MODELO` não é consultado.

**`especializado`** (o caminho original). A regra de escolha, em ordem:

1. **Corte e cor cabem nas opções do modelo principal** (`AI_MODELO`, o
   `change-haircut`) → ele mesmo, com os valores exatos das opções. É o caminho
   especializado e o primeiro a ser tentado.
2. **O modelo principal aceita texto livre nesses campos** (se o schema publicado não tiver
   lista de opções) → ele mesmo, com a descrição.
3. **Descrição livre** que não cabe nas opções, ou **tipo de cabelo escolhido** (o modelo
   principal não tem esse campo) → modelo de edição por texto (`AI_MODELO_TEXTO`), com
   instrução montada em `instrucoes.py`.

O gênero do corte (`gender`) só existe no modelo principal e vai a ele nos caminhos 1 e 2,
com o valor escolhido na tela. No caminho 3 o modelo de texto não tem esse campo: o gênero
escolhido vira uma frase da instrução (`instrucoes.py`).

Cada modelo de edição por instrução recebe a foto e os parâmetros de um jeito (`Perfil`): o
Kontext tem `input_image` (uma URL), o Nano Banana tem `image_input` (uma lista de URLs),
`resolution` e as buscas na web (`google_search`, `image_search`), que vão sempre desligadas:
a foto do cliente não pode servir de consulta a uma busca. O perfil sai do identificador do
modelo, e o schema publicado confere os nomes antes do envio.

Quando o schema ao vivo não está disponível (provedor local, ou a prévia no aplicativo),
a escolha usa o que o catálogo sabe dos valores das opções. Na geração de verdade, o
schema publicado pela Replicate é consultado e tem a palavra final.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from collections.abc import Sequence
from typing import Any, Literal

from app.core.erros import ValidacaoFalhou
from app.services.ai.base import FalhaDoProvedor
from app.services.ai.esquema import EsquemaModelo
from app.services.ai.instrucoes import (
    Estrategia,
    descrever,
    prompt_detalhado,
    prompt_detalhado_original,
    prompt_edicao,
)
from app.services.ai.pedido import GENERO_PADRAO, Alteracao, PedidoCapilar

log = logging.getLogger(__name__)

#: Valor do `change-haircut` para "não mexer" (é o padrão do próprio modelo).
SEM_MUDANCA = "No change"

#: Os modelos do caminho especializado (change-haircut e Kontext) recebem a foto do
#: cliente neste campo.
CAMPO_IMAGEM = "input_image"

#: Caminho das simulações (`AI_ESTRATEGIA`).
Caminho = Literal["especializado", "instrucao"]

#: Gênero do corte no `change-haircut` ("none", "male" ou "female").
CAMPO_GENERO = "gender"


class Modo(StrEnum):
    #: Modelo principal com valores das opções fechadas.
    opcoes = "opcoes"
    #: Descrição livre (no modelo de edição por texto, ou no principal se ele aceitar).
    descricao = "descricao"
    #: Caminho `instrucao`: todo pedido vira uma instrução escrita detalhada.
    instrucao = "instrucao"


DESCRICAO_DO_MODO = {
    Modo.opcoes: "Troca de corte e cor com as opções do modelo especializado",
    Modo.descricao: "Edição a partir da descrição escrita",
    Modo.instrucao: "Edição a partir de uma instrução detalhada do corte e da cor",
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
    #: Em que campo vai a foto, e se dentro de uma lista (`image_input` do Nano Banana).
    campo_imagem: str = CAMPO_IMAGEM
    imagem_em_lista: bool = False

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
    caminho: Caminho = "especializado"
    #: Resolução para os modelos que têm o campo `resolution`.
    resolucao: str = "1K"
    #: Qual instrução detalhada usar. A produção usa sempre "preservacao"; "original" (a
    #: de 2026-11-05) existe só para o script de comparação medir a diferença.
    variante_instrucao: Literal["preservacao", "original"] = "preservacao"


def configuracao_de(config) -> Configuracao:
    return Configuracao(
        modelo_principal=config.ai_modelo,
        modelo_texto=config.ai_modelo_texto,
        estrategia=config.ai_instrucao_idioma,
        caminho=config.ai_estrategia,
        resolucao=config.ai_resolucao,
    )


COMUNS = {"aspect_ratio": "match_input_image", "output_format": "jpg"}


@dataclass(frozen=True)
class Perfil:
    """Como um modelo de edição por instrução recebe a foto, os parâmetros e a instrução."""

    campo_imagem: str
    imagem_em_lista: bool
    #: Parâmetros que acompanham a instrução. Os que o schema publicado não tiver saem do
    #: envio (`montar_entrada`), e o modelo usa o padrão dele.
    acessorios: dict[str, Any]
    #: Instrução longa (`prompt_detalhado`) em vez da curta do Kontext.
    instrucao_detalhada: bool


#: FLUX Kontext (o `flux-kontext-pro` do caminho atual): foto em `input_image`.
PERFIL_KONTEXT = Perfil(CAMPO_IMAGEM, False, COMUNS, False)


def perfil_de(modelo: str, resolucao: str = "1K") -> Perfil:
    """O perfil do modelo, pelo identificador. Modelo desconhecido segue o do Kontext.

    Nano Banana (`google/nano-banana-2.1`, schema conferido em docs/NANO_BANANA.md): a foto
    vai em `image_input`, uma lista; a proporção acompanha a foto; e as buscas na web ficam
    explicitamente desligadas (o padrão publicado também é desligado, mas o envio não
    depende disso).
    """
    if modelo.startswith("google/nano-banana"):
        return Perfil(
            campo_imagem="image_input",
            imagem_em_lista=True,
            acessorios={
                "aspect_ratio": "match_input_image",
                "resolution": resolucao,
                "output_format": "jpg",
                "google_search": False,
                "image_search": False,
            },
            instrucao_detalhada=True,
        )
    return PERFIL_KONTEXT


def _plano_de_instrucao(pedido: PedidoCapilar, config: Configuracao, modo: Modo) -> Plano:
    """O pedido inteiro como instrução escrita ao modelo de texto, no formato do perfil dele."""
    perfil = perfil_de(config.modelo_texto, config.resolucao)
    if not perfil.instrucao_detalhada:
        construir = prompt_edicao
    elif config.variante_instrucao == "original":
        construir = prompt_detalhado_original
    else:
        construir = prompt_detalhado
    return Plano(
        modo=modo,
        modelo=config.modelo_texto,
        campos={"prompt": construir(pedido, config.estrategia), **perfil.acessorios},
        essenciais=frozenset({"prompt", perfil.campo_imagem}),
        campo_imagem=perfil.campo_imagem,
        imagem_em_lista=perfil.imagem_em_lista,
    )


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
    if config.caminho == "instrucao":
        # A configuração recusa este caminho sem modelo de texto (`config.py`).
        return _plano_de_instrucao(pedido, config, Modo.instrucao)

    # O modelo principal não tem campo de tipo de cabelo: com um tipo escolhido, o pedido
    # vai direto ao modelo de edição por texto, que recebe o tipo como frase da instrução.
    if pedido.textura is not None:
        return _plano_de_texto(pedido, config)

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
    return _plano_de_texto(pedido, config)


def _plano_de_texto(pedido: PedidoCapilar, config: Configuracao) -> Plano:
    if not config.modelo_texto:
        raise ValidacaoFalhou(
            "A descrição livre está desligada neste servidor (AI_MODELO_TEXTO vazio). "
            "Use exatamente um dos exemplos da tela, ou peça para ligar a descrição livre.",
            codigo="descricao_livre_indisponivel",
        )
    return _plano_de_instrucao(pedido, config, Modo.descricao)


def montar_entrada(
    plano: Plano,
    imagem: str,
    esquema: EsquemaModelo | None,
    referencias: Sequence[str] = (),
) -> dict[str, Any]:
    """Junta a imagem e os parâmetros e confere tudo contra o schema publicado do modelo.

    Campo que o modelo não tem: se for essencial, a geração para (`modelo_incompativel`);
    se for acessório (proporção, formato), sai do envio e o modelo usa o padrão dele.
    Valor fora das opções: mesma regra (`parametro_fora_do_schema`). Sem schema (provedor
    local), segue como está.

    `referencias` (só no experimento) vão depois da foto, na mesma lista, na ordem em que
    a instrução as descreve. Um modelo que recebe uma imagem só não tem onde pô-las.
    """
    if referencias and not plano.imagem_em_lista:
        raise FalhaDoProvedor(
            f"O modelo {plano.modelo} recebe uma imagem só: não há onde enviar referências.",
            codigo="modelo_incompativel",
        )
    entrada: dict[str, Any] = {
        plano.campo_imagem: [imagem, *referencias] if plano.imagem_em_lista else imagem,
        **plano.campos,
    }
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
