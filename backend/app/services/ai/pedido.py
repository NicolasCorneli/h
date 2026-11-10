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

#: Tipo de cabelo **desejado** na simulação, escolhido na etapa "Estilo e cor": a
#: categoria ("liso", "ondulado", "cacheado", "crespo") ou o tipo detalhado (1A a 4C, da
#: classificação usada em salões). Ausente (None) é "Manter meu tipo de cabelo atual": uma
#: instrução positiva de preservar a textura da foto, e não falta de informação. Não é
#: parâmetro de nenhum modelo; entra como frase da instrução (`instrucoes.py`).
#:
#: Até 2026-11-10 a mesma lista servia para informar o cabelo *natural* (campo
#: `curvatura`), só como apoio à leitura da foto. O significado mudou, e por isso o valor
#: novo tem campo próprio (`textura`), sem reaproveitar o antigo.
CATEGORIAS_DE_TEXTURA: tuple[str, ...] = ("liso", "ondulado", "cacheado", "crespo")
TIPOS_DE_TEXTURA: tuple[str, ...] = tuple(f"{n}{l}" for n in "1234" for l in "ABC")
TEXTURAS: tuple[str, ...] = CATEGORIAS_DE_TEXTURA + TIPOS_DE_TEXTURA

#: Papel de cada imagem que acompanha a foto do cliente. O aplicativo não envia
#: referências (a foto de referência saiu do escopo, ver a migration c6a2f9d41b87); elas
#: existem para o experimento de `scripts/comparar_simulacoes.py`.
Papel = Literal["corte", "textura"]

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
    #: Descrição completa em inglês, quando o texto é um nome do catálogo: é a que vai nas
    #: instruções detalhadas (`instrucoes.prompt_detalhado`).
    detalhe: str | None = None
    #: De qual campo veio: alguns termos mudam de sentido ("degradê" é um corte no corte e
    #: uma transição de cor na cor), e o glossário precisa saber.
    campo: Literal["corte", "cor"] = "corte"

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
    #: Tipo de cabelo desejado (`TEXTURAS`), ou None ("Manter meu tipo de cabelo atual").
    textura: str | None = None
    #: Papéis das imagens de referência que seguem a foto, na ordem (só no experimento).
    referencias: tuple[Papel, ...] = ()

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
    return Alteracao(opcao.rotulo, opcao.ingles, opcao.opcoes_do_modelo, opcao.detalhe or None)


def alteracao_de_cor(texto: str) -> Alteracao:
    opcao = opcao_de_cor(texto)
    if opcao is None:
        return Alteracao(texto, campo="cor")
    return Alteracao(
        opcao.rotulo, opcao.ingles, opcao.opcoes_do_modelo, opcao.detalhe or None, campo="cor"
    )


def validar_genero(genero: str | None) -> Genero:
    """Só os valores aceitos pelo modelo passam. Ausente é o padrão, "none"."""
    if genero is None or genero == "":
        return GENERO_PADRAO
    if genero not in GENEROS:
        raise ValidacaoFalhou(
            "Gênero inválido: escolha feminino, masculino ou neutro.",
            codigo="genero_invalido",
            detalhes=[{"campo": "genero", "permitidos": list(GENEROS)}],
        )
    return cast(Genero, genero)


def validar_textura(textura: str | None) -> str | None:
    """Só os valores da lista passam. Ausente ou vazio é "Manter meu tipo de cabelo atual"."""
    if textura is None or textura.strip() == "":
        return None
    valor = textura.strip()
    valor = valor.upper() if len(valor) == 2 else valor.lower()
    if valor not in TEXTURAS:
        raise ValidacaoFalhou(
            "Tipo de cabelo inválido: escolha liso, ondulado, cacheado, crespo, um tipo de 1A "
            "a 4C, ou manter o tipo atual.",
            codigo="textura_invalida",
            detalhes=[{"campo": "textura", "permitidos": list(TEXTURAS)}],
        )
    return valor


def interpretar(
    corte: str | None,
    cor: str | None,
    *,
    manter_corte: bool = False,
    manter_cor: bool = False,
    genero: str | None = GENERO_PADRAO,
    textura: str | None = None,
) -> PedidoCapilar:
    """Valida e monta o pedido. Levanta 422 com código próprio para cada caso.

    Manter o corte, a cor e o tipo de cabelo ao mesmo tempo não é pedido: não há o que
    simular. Manter o corte e a cor e mudar só o tipo de cabelo, sim.
    """
    genero_valido = validar_genero(genero)
    textura_valida = validar_textura(textura)
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
    if manter_corte and manter_cor and textura_valida is None:
        raise ValidacaoFalhou(
            "Nada a simular: escolha mudar o corte, a cor ou o tipo de cabelo.",
            codigo="pedido_vazio",
        )

    return PedidoCapilar(
        corte=alteracao_de_corte(texto_corte) if texto_corte else None,
        cor=alteracao_de_cor(texto_cor) if texto_cor else None,
        genero=genero_valido,
        textura=textura_valida,
    )


def pedido_registrado(
    estilo: str, cor: str, genero: str = GENERO_PADRAO, textura: str | None = None
) -> PedidoCapilar:
    """Reconstrói o pedido a partir do que ficou gravado na simulação.

    O processamento em segundo plano recebe só o identificador; o pedido volta daqui, com
    as mesmas regras da criação.
    """
    corte = None if estilo in (CORTE_MANTIDO, "") else alteracao_de_corte(estilo)
    tom = None if cor in (COR_MANTIDA, "") else alteracao_de_cor(cor)
    return PedidoCapilar(
        corte=corte, cor=tom, genero=validar_genero(genero), textura=validar_textura(textura)
    )
