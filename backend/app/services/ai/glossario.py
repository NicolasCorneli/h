"""Termos de cabeleireiro em português e o equivalente em inglês.

Os modelos FLUX Kontext usam um codificador de texto treinado majoritariamente em inglês,
e a documentação de prompts da Black Forest Labs é toda em inglês. A descrição que o
profissional escreve, porém, é em português e tem detalhes que não podem se perder
("franja cortininha", "degradê baixo nas laterais").

A estratégia adotada (decisão registrada no relatório) é **não traduzir** a descrição: ela
vai ao modelo como foi escrita, e este glossário só acrescenta, ao lado, os termos técnicos
reconhecidos em inglês. Assim nada do que o usuário escreveu é descartado, e o modelo
recebe as palavras-chave na língua em que foi treinado. Se o teste real mostrar que outra
estratégia funciona melhor, ela muda aqui e em `instrucoes.py`, em um lugar só.
"""

from __future__ import annotations

import re

from app.services.texto import normalizar

#: (padrões em português, sem acento e em minúsculas; termo em inglês). Os padrões mais
#: longos são procurados primeiro, e um trecho já reconhecido não é reaproveitado: em
#: "castanho escuro" sai "dark brown", e não também "brown".
TERMOS: tuple[tuple[tuple[str, ...], str], ...] = (
    # Franja
    (("franja cortininha", "franja cortina", "franja de cortina"), "curtain bangs"),
    (("franja reta",), "blunt bangs"),
    (("franja lateral", "franja de lado", "franja para o lado"), "side-swept bangs"),
    (("franja",), "bangs"),
    # Formatos de corte
    (("long bob", "lob"), "long bob"),
    (("chanel de bico", "chanel bico"), "angled bob"),
    (("chanel", "bob"), "bob"),
    (("pixie", "joaozinho"), "pixie cut"),
    (("degrade baixo", "low fade"), "low fade"),
    (("degrade medio", "mid fade"), "mid fade"),
    (("degrade alto", "high fade"), "high fade"),
    (("degrade", "fade", "disfarcado"), "fade"),
    (("undercut",), "undercut"),
    (("moicano",), "mohawk"),
    (("topete",), "quiff"),
    (("mullet",), "mullet"),
    (("shaggy", "shag"), "shag cut"),
    (("butterfly", "corte borboleta"), "butterfly cut"),
    (("texturizado", "texturizada"), "textured"),
    (("estruturado", "estruturada"), "structured"),
    (("repicado", "repicada", "picotado", "picotada"), "choppy layers"),
    (("desfiado", "desfiada", "desfiadas", "desfiados"), "wispy textured ends"),
    (("em camadas", "camadas", "camada"), "layers"),
    (("maquina zero", "raspado", "raspada", "maquina"), "buzzed"),
    (("corte militar", "militar"), "crew cut"),
    (("corte social",), "classic short men's cut"),
    # Regiões e comprimentos
    (("nas laterais", "laterais", "dos lados", "nos lados"), "sides"),
    (("no topo", "em cima", "topo"), "top"),
    (("nuca",), "nape"),
    (("na altura do queixo", "altura do queixo", "queixo"), "chin-length"),
    (
        ("na altura dos ombros", "altura dos ombros", "na altura do ombro", "ombros", "ombro"),
        "shoulder-length",
    ),
    (("na altura da orelha", "orelhas", "orelha"), "ear-length"),
    (("muito curto", "muito curta", "curtinho", "curtinha"), "very short"),
    (("curto", "curta"), "short"),
    (("medio", "media"), "medium-length"),
    (("longo", "longa", "comprido", "comprida"), "long"),
    (("preservar o comprimento", "preserve o comprimento", "manter o comprimento", "mesmo comprimento", "sem tirar comprimento"), "keep the current length"),
    # Textura e acabamento
    (("cacheado", "cacheada", "cachos", "cacho"), "curly"),
    (("ondulado", "ondulada", "ondas"), "wavy"),
    (("crespo", "crespa", "black power"), "coily afro-textured"),
    (("liso", "lisa", "escorrido", "escorrida"), "straight"),
    (("textura natural",), "natural texture"),
    (("volume",), "volume"),
    (("assimetrico", "assimetrica"), "asymmetrical"),
    (("risca lateral", "risca de lado", "repartido de lado"), "side part"),
    (("risca no meio", "risca ao meio", "repartido ao meio"), "middle part"),
    (("suave", "suaves"), "soft"),
    (("coque",), "bun"),
    (("rabo de cavalo",), "ponytail"),
    (("trancas", "tranca"), "braids"),
    # Cores
    (("loiro platinado", "loira platinada", "platinado", "platinada"), "platinum blonde"),
    (("loiro mel", "loira mel"), "honey blonde"),
    (("loiro", "loira"), "blonde"),
    (("castanho escuro", "castanha escura"), "dark brown"),
    (("castanho claro", "castanha clara"), "light brown"),
    (("castanho medio",), "medium brown"),
    (("castanho", "castanha"), "brown"),
    (("chocolate",), "chocolate brown"),
    (("caramelo",), "caramel"),
    (("mel",), "honey"),
    (("bege",), "beige"),
    (("dourado", "dourada"), "golden"),
    (("preto azulado", "azulado"), "blue-black"),
    (("preto", "preta", "negro", "negra"), "black"),
    (("ruivo", "ruiva"), "ginger red"),
    (("acobreado", "acobreada", "cobre"), "copper"),
    (("vermelho", "vermelha"), "red"),
    (("marsala", "vinho", "borgonha", "bordo"), "burgundy"),
    (("manteiga",), "butter"),
    (("canela",), "cinnamon"),
    (("iluminada", "iluminado"), "with highlights"),
    (("mogno",), "mahogany"),
    (("cinza", "grisalho", "grisalha", "prata", "prateado", "prateada"), "silver gray"),
    (("branco", "branca"), "white"),
    (("rosa", "rose"), "pink"),
    (("azul",), "blue"),
    (("roxo", "roxa", "violeta", "lilas"), "purple"),
    (("verde",), "green"),
    (("reflexos", "luzes", "mechas"), "highlights"),
    (("ombre",), "ombre"),
    (("raiz", "raizes"), "roots"),
    (("frio", "fria"), "cool-toned"),
    (("quente",), "warm-toned"),
    (("escuro", "escura"), "dark"),
    (("claro", "clara"), "light"),
    (("intenso", "intensa", "vibrante"), "vivid"),
    (("natural",), "natural"),
)


def _padroes() -> list[tuple[re.Pattern[str], str]]:
    pares = [(padrao, ingles) for padroes, ingles in TERMOS for padrao in padroes]
    pares.sort(key=lambda par: len(par[0]), reverse=True)
    return [(re.compile(rf"\b{re.escape(padrao)}\b"), ingles) for padrao, ingles in pares]


_PADROES = _padroes()


def termos_em_ingles(texto: str) -> list[str]:
    """Termos técnicos reconhecidos no texto, na ordem em que aparecem, sem repetição."""
    base = normalizar(texto)
    ocupado = [False] * len(base)
    achados: list[tuple[int, str]] = []
    for padrao, ingles in _PADROES:
        for encontro in padrao.finditer(base):
            inicio, fim = encontro.span()
            if any(ocupado[inicio:fim]):
                continue
            for i in range(inicio, fim):
                ocupado[i] = True
            achados.append((inicio, ingles))
    achados.sort()
    vistos: list[str] = []
    for _, ingles in achados:
        if ingles not in vistos:
            vistos.append(ingles)
    return vistos
