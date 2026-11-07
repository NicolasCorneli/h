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
    #: Descrição completa em inglês, para os modelos que seguem instruções longas (o Nano
    #: Banana, no caminho `instrucao`). Diz comprimento, formato e acabamento, que o nome
    #: curto deixa por conta do modelo. A descrição curta (`ingles`) continua sendo a do
    #: Kontext, para o caminho atual não mudar.
    detalhe: str = ""


CORTES_EM_ALTA: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Long bob estruturado", "structured long bob (lob) with clean lines, just above the shoulders", ("Lob",), detalhe="a structured long bob (lob): the hair ends just above the shoulders, slightly longer in front than in the back, with a clean, blunt perimeter and defined lines"),
    OpcaoCatalogo("Bob texturizado", "textured bob with soft layers and movement", detalhe="a textured bob ending between the jawline and the chin, with soft internal layers, piecey ends and natural movement"),
    OpcaoCatalogo("Butterfly", "butterfly haircut: short face-framing layers and longer layers in the back", detalhe="a butterfly haircut: long hair with short face-framing layers that start around the cheekbones and longer feathered layers in the back, with volume and bounce"),
    OpcaoCatalogo("Shaggy com franja", "shaggy haircut with bangs", detalhe="a shaggy haircut with bangs: choppy, feathered layers all over the head, tousled texture and wispy bangs over the forehead"),
    OpcaoCatalogo("Chanel de bico", "angled bob, shorter in the back and longer in front", ("Angled Bob",), detalhe="an angled bob: shorter at the nape and gradually longer toward the front, where the ends reach around the chin"),
    OpcaoCatalogo("Degradê", "fade haircut: very short on the sides, longer on top", detalhe="a fade haircut: the sides and back are clipped very short and blend gradually into longer hair on top, which keeps a few centimeters of length"),
    OpcaoCatalogo("Mullet moderno", "modern mullet", detalhe="a modern mullet: short, textured layers on the top and sides and noticeably longer hair at the back of the neck, blended rather than disconnected"),
    OpcaoCatalogo("Texturizado curto", "short textured crop", detalhe="a short textured crop: short hair on top with choppy, slightly messy texture pushed forward, and shorter tapered sides"),
)

CORTES_CLASSICOS: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Chanel", "classic chin-length bob with a straight base", ("Bob",), detalhe="a classic chin-length bob: all the hair cut to the same length around the jawline, with a blunt, even perimeter"),
    OpcaoCatalogo("Pixie", "pixie cut", ("Pixie Cut",), detalhe="a pixie cut: very short hair on the back and sides, slightly longer on top, with soft, wispy pieces around the face and forehead"),
    OpcaoCatalogo("Camadas longas", "long layered haircut", ("Layered",), detalhe="long layered hair: the length stays below the shoulders, with long, blended layers that add movement and frame the face"),
    OpcaoCatalogo("Franja reta", "blunt bangs", ("Blunt Bangs",), detalhe="blunt bangs: a full fringe with an even, horizontal cut line at or just above the eyebrows; the rest of the hair keeps its current length"),
    OpcaoCatalogo("Corte social", "classic short men's haircut, tapered sides", detalhe="a classic short men's haircut: short, neat hair with tapered sides and back, slightly longer on top and neatly combed"),
    OpcaoCatalogo("Caesar", "caesar cut: short, even length all over, with short straight bangs", detalhe="a Caesar cut: short hair of even length all over, brushed forward, with a short fringe cut in an even, horizontal line on the forehead"),
)

CORES_EM_ALTA: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Loiro manteiga", "butter blonde: soft, warm medium blonde", (), "#D6B677", detalhe="butter blonde: a soft, creamy, warm medium blonde, golden but not brassy"),
    OpcaoCatalogo("Loiro mel", "honey blonde", ("Honey Blonde",), "#C79A5B", detalhe="honey blonde: a warm golden blonde with amber tones"),
    OpcaoCatalogo("Morena iluminada", "brunette with fine honey and caramel highlights", (), "#6B4A33", detalhe="brunette hair with fine, blended honey and caramel highlights, brighter around the face and on the ends, over a natural brown base"),
    OpcaoCatalogo("Chocolate quente", "warm chocolate brown with subtle golden reflections", (), "#5A3A28", detalhe="warm chocolate brown: a rich medium-dark brown with subtle golden reflections in the light"),
    OpcaoCatalogo("Cobre canela", "cinnamon copper: deep copper red mixed with brown", (), "#8E4A2C", detalhe="cinnamon copper: a deep, warm copper red blended with brown"),
    OpcaoCatalogo("Vermelho bordô", "burgundy red", ("Burgundy",), "#6E1F2A", detalhe="burgundy: a deep wine red with purple undertones"),
)

CORES_CLASSICAS: tuple[OpcaoCatalogo, ...] = (
    OpcaoCatalogo("Preto natural", "natural black", ("Black",), "#1E1A18", detalhe="natural black: a soft natural black with subtle shine, not blue-black"),
    OpcaoCatalogo("Castanho-escuro", "dark brown", ("Dark Brown",), "#3B2A22", detalhe="dark brown: a deep, natural brown"),
    OpcaoCatalogo("Castanho-claro", "light brown", ("Light Brown",), "#8A6345", detalhe="light brown: a soft, natural light brown"),
    OpcaoCatalogo("Loiro", "blonde", ("Blonde",), "#C9A46A", detalhe="natural blonde: a medium golden blonde"),
    OpcaoCatalogo("Ruivo", "natural ginger red", ("Copper",), "#B5562B", detalhe="natural ginger red: a vivid but natural orange-copper red"),
    OpcaoCatalogo("Grisalho", "natural silver gray", ("Silver",), "#A7A9AC", detalhe="natural silver gray: an even, silvery gray with natural cool tones"),
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
