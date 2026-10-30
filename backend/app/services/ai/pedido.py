"""O pedido de personalização: o que mudar no cabelo, do jeito que o profissional pediu.

É o contrato entre a tela "Estilo e cor" e o servidor. O aplicativo manda texto (o corte
e a cor descritos pelo profissional), duas marcas, "manter o corte" e "manter a cor", e o
gênero do corte (`GENEROS`). Aqui o texto é limpo e validado, e cada parte vira uma
`Alteracao`:

- quando o texto é um dos nomes conhecidos do catálogo (os exemplos que a tela mostra), ela
  leva a descrição em inglês e, se houver, os valores equivalentes nas opções fechadas do
  modelo principal;
- quando é texto livre, segue como foi escrito, sem tradução nem resumo.

A escolha do modelo e a montagem dos parâmetros ficam em `planos.py`. Este módulo não
sabe nada da Replicate.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, cast

from app.core.erros import ValidacaoFalhou
from app.services.catalogo import opcao_de_cor, opcao_de_corte

MAX_DESCRICAO = 300

#: Rótulos gravados em `simulacoes.estilo` e `simulacoes.cor` quando nada muda. São o que
#: aparece no histórico ("Corte atual · Loiro") e o que permite reconstruir o pedido.
CORTE_MANTIDO = "Corte atual"
COR_MANTIDA = "Cor atual"

#: Gênero do corte, com os valores exatos do campo `gender` do `change-haircut`. "none" é o
#: padrão do próprio modelo: é o que valia antes de a tela ter a opção, e o que vale quando
#: o aplicativo não manda nada.
Genero = Literal["none", "male", "female"]
GENEROS: tuple[Genero, ...] = ("none", "male", "female")
GENERO_PADRAO: Genero = "none"

#: Letras (com acento), números, espaço e a pontuação de uma frase comum. Ficam de fora os
#: sinais que só servem para montar código ou marcação: < > { } [ ] \ | ` $ @ # * ~ ^ =.
_PERMITIDO = re.compile(r"^[\w\s.,;:!?()'\"/+&%ºª°-]*$")
_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass(frozen=True)
class Alteracao:
    #: Como foi escrito (ou o nome do catálogo, quando é um deles). É o que o histórico mostra.
    texto: str
    #: Descrição em inglês, quando o texto é um nome do catálogo.
    ingles: str | None = None
    #: Valores equivalentes nas opções fechadas do modelo principal, em ordem de
    #: preferência. Vazio quando não há equivalente (ex.: "Butterfly").
    opcoes_do_modelo: tuple[str, ...] = ()

    @property
    def do_catalogo(self) -> bool:
        return self.ingles is not None


@dataclass(frozen=True)
class PedidoCapilar:
    #: None: manter o corte atual.
    corte: Alteracao | None
    #: None: manter a cor atual.
    cor: Alteracao | None
    genero: Genero = GENERO_PADRAO

    @property
    def rotulo_corte(self) -> str:
        return self.corte.texto if self.corte is not None else CORTE_MANTIDO

    @property
    def rotulo_cor(self) -> str:
        return self.cor.texto if self.cor is not None else COR_MANTIDA


def limpar_descricao(texto: str | None, campo: str) -> str:
    """Normaliza espaços e recusa o que não é uma descrição em linguagem comum."""
    if not texto:
        return ""
    limpo = _CONTROLE.sub(" ", unicodedata.normalize("NFC", texto))
    limpo = re.sub(r"\s+", " ", limpo).strip()
    if not limpo:
        # Só espaços é o mesmo que não escrever nada: quem decide o que falta é `interpretar`.
        return ""
    if len(limpo) > MAX_DESCRICAO:
        raise ValidacaoFalhou(
            f"A descrição passa de {MAX_DESCRICAO} caracteres. Resuma o essencial.",
            codigo="descricao_longa",
            detalhes=[{"campo": campo, "maximo": MAX_DESCRICAO}],
        )
    if not _PERMITIDO.match(limpo):
        raise ValidacaoFalhou(
            "Use só letras, números e pontuação comum na descrição.",
            codigo="descricao_invalida",
            detalhes=[{"campo": campo}],
        )
    if sum(1 for c in limpo if c.isalpha()) < 2:
        raise ValidacaoFalhou(
            "Descreva com palavras o que você quer.",
            codigo="descricao_invalida",
            detalhes=[{"campo": campo}],
        )
    return limpo


def alteracao_de_corte(texto: str) -> Alteracao:
    opcao = opcao_de_corte(texto)
    if opcao is None:
        return Alteracao(texto)
    return Alteracao(opcao.rotulo, opcao.ingles, opcao.opcoes_do_modelo)


def alteracao_de_cor(texto: str) -> Alteracao:
    opcao = opcao_de_cor(texto)
    if opcao is None:
        return Alteracao(texto)
    return Alteracao(opcao.rotulo, opcao.ingles, opcao.opcoes_do_modelo)


def validar_genero(genero: str | None) -> Genero:
    """Só os valores aceitos pelo modelo passam. Ausente é o padrão, "none"."""
    if genero is None or genero == "":
        return GENERO_PADRAO
    if genero not in GENEROS:
        raise ValidacaoFalhou(
            "Gênero inválido: escolha feminino, masculino ou não especificar.",
            codigo="genero_invalido",
            detalhes=[{"campo": "genero", "permitidos": list(GENEROS)}],
        )
    return cast(Genero, genero)


def interpretar(
    corte: str | None,
    cor: str | None,
    *,
    manter_corte: bool = False,
    manter_cor: bool = False,
    genero: str | None = GENERO_PADRAO,
) -> PedidoCapilar:
    """Valida e monta o pedido. Levanta 422 com código próprio para cada caso."""
    genero_valido = validar_genero(genero)
    texto_corte = "" if manter_corte else limpar_descricao(corte, "corte")
    texto_cor = "" if manter_cor else limpar_descricao(cor, "cor")

    if not manter_corte and not texto_corte:
        raise ValidacaoFalhou(
            "Descreva o corte ou marque \"Manter o corte atual\".",
            codigo="corte_vazio",
            detalhes=[{"campo": "corte"}],
        )
    if not manter_cor and not texto_cor:
        raise ValidacaoFalhou(
            "Descreva a cor ou marque \"Manter a cor atual\".",
            codigo="cor_vazia",
            detalhes=[{"campo": "cor"}],
        )
    if manter_corte and manter_cor:
        raise ValidacaoFalhou(
            "Nada a simular: escolha mudar o corte, a cor ou os dois.",
            codigo="pedido_vazio",
        )

    return PedidoCapilar(
        corte=alteracao_de_corte(texto_corte) if texto_corte else None,
        cor=alteracao_de_cor(texto_cor) if texto_cor else None,
        genero=genero_valido,
    )


def pedido_registrado(estilo: str, cor: str, genero: str = GENERO_PADRAO) -> PedidoCapilar:
    """Reconstrói o pedido a partir do que ficou gravado na simulação.

    O processamento em segundo plano recebe só o identificador; o pedido volta daqui, com
    as mesmas regras da criação.
    """
    corte = None if estilo in (CORTE_MANTIDO, "") else alteracao_de_corte(estilo)
    tom = None if cor in (COR_MANTIDA, "") else alteracao_de_cor(cor)
    return PedidoCapilar(corte=corte, cor=tom, genero=validar_genero(genero))
