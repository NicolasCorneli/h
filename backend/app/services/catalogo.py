"""Catálogo: os exemplos de corte e de cor que a tela "Estilo e cor" mostra, e os serviços.

Decisão registrada no diagnóstico (§4.12): o catálogo **não** virou tabela, porque é fixo e
faz parte da lógica da aplicação. Corte e cor são descritos livremente; os exemplos só
mostram o que pode ser pedido. Foram escolhidos a partir de matérias de tendência de 2026
(cortes e cores "em alta") e dos cortes e tons que não saem de moda ("clássicos"). Não há
ranking oficial de pedidos em salões: a seleção está justificada no relatório.

Quando o texto recebido é exatamente um dos exemplos (sem diferenciar caixa, acento ou
hífen), o servidor:

1. usa a descrição em inglês do exemplo nas instruções em texto;
2. se houver, usa o valor equivalente nas opções fechadas do modelo principal
   (`change-haircut`), que recebe `haircut` e `hair_color` de uma lista publicada no schema
   dele. A geração confere o valor contra o schema ao vivo antes de enviar; exemplo sem
   equivalente vai pelo modelo de edição por texto.

`GET /api/v1/catalogo` publica os nomes. O aplicativo tem a mesma lista em
`espelho/src/data/catalogo.ts`, e um teste confere que as duas não divergem.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.texto import normalizar


@dataclass(frozen=True)
class OpcaoCatalogo:
    rotulo: str
    #: Descrição em inglês, usada nas instruções em texto.
    ingles: str
    #: Valores equivalentes nas opções fechadas do modelo principal, em ordem de
    #: preferência. Vazio: sem equivalente.
    opcoes_do_modelo: tuple[str, ...] = ()
    #: Amostra de cor (só nas cores), usada pelo provedor local de desenvolvimento.
    amostra: str | None = None


CORTES_EM_ALTA: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Long bob estruturado", "structured long bob (lob) with clean lines, just above the shoulders", ("Lob",)),
    OpcaoCatalogo("Bob texturizado", "textured bob with soft layers and movement"),
    OpcaoCatalogo("Butterfly", "butterfly haircut: short face-framing layers and longer layers in the back"),
    OpcaoCatalogo("Shaggy com franja", "shaggy haircut with bangs"),
    OpcaoCatalogo("Chanel de bico", "angled bob, shorter in the back and longer in front", ("Angled Bob",)),
    OpcaoCatalogo("Degradê", "fade haircut: very short on the sides, longer on top"),
    OpcaoCatalogo("Mullet moderno", "modern mullet"),
    OpcaoCatalogo("Texturizado curto", "short textured crop"),
)

CORTES_CLASSICOS: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Chanel", "classic chin-length bob with a straight base", ("Bob",)),
    OpcaoCatalogo("Pixie", "pixie cut", ("Pixie Cut",)),
    OpcaoCatalogo("Camadas longas", "long layered haircut", ("Layered",)),
    OpcaoCatalogo("Franja reta", "blunt bangs", ("Blunt Bangs",)),
    OpcaoCatalogo("Corte social", "classic short men's haircut, tapered sides"),
    OpcaoCatalogo("Caesar", "caesar cut: short, even length all over, with short straight bangs"),
)

CORES_EM_ALTA: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Loiro manteiga", "butter blonde: soft, warm medium blonde", (), "#D6B677"),
    OpcaoCatalogo("Loiro mel", "honey blonde", ("Honey Blonde",), "#C79A5B"),
    OpcaoCatalogo("Morena iluminada", "brunette with fine honey and caramel highlights", (), "#6B4A33"),
    OpcaoCatalogo("Chocolate quente", "warm chocolate brown with subtle golden reflections", (), "#5A3A28"),
    OpcaoCatalogo("Cobre canela", "cinnamon copper: deep copper red mixed with brown", (), "#8E4A2C"),
    OpcaoCatalogo("Vermelho bordô", "burgundy red", ("Burgundy",), "#6E1F2A"),
)

CORES_CLASSICAS: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Preto natural", "natural black", ("Black",), "#1E1A18"),
    OpcaoCatalogo("Castanho-escuro", "dark brown", ("Dark Brown",), "#3B2A22"),
    OpcaoCatalogo("Castanho-claro", "light brown", ("Light Brown",), "#8A6345"),
    OpcaoCatalogo("Loiro", "blonde", ("Blonde",), "#C9A46A"),
    OpcaoCatalogo("Ruivo", "natural ginger red", ("Copper",), "#B5562B"),
    OpcaoCatalogo("Grisalho", "natural silver gray", ("Silver",), "#A7A9AC"),
)

CORTES = CORTES_EM_ALTA + CORTES_CLASSICOS
CORES = CORES_EM_ALTA + CORES_CLASSICAS

SERVICOS: tuple[str, ...] = ("Coloração", "Corte", "Hidratação", "Escova", "Retoque de cor")


def _chave(texto: str) -> str:
    return normalizar(texto).rstrip(" .")


_CORTES_POR_CHAVE = {_chave(o.rotulo): o for o in CORTES}
_CORES_POR_CHAVE = {_chave(o.rotulo): o for o in CORES}


def opcao_de_corte(texto: str) -> OpcaoCatalogo | None:
    """O exemplo de corte cujo nome é exatamente o texto, se houver."""
    return _CORTES_POR_CHAVE.get(_chave(texto))


def opcao_de_cor(texto: str) -> OpcaoCatalogo | None:
    """O exemplo de cor cujo nome é exatamente o texto, se houver."""
    return _CORES_POR_CHAVE.get(_chave(texto))


def rotulos_de_estilo() -> list[str]:
    return [opcao.rotulo for opcao in CORTES]


def rotulos_de_cor() -> list[str]:
    return [opcao.rotulo for opcao in CORES]
