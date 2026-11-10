"""Instrução enviada ao modelo de edição por texto (`prompt`).

Só o modelo que tem o campo `prompt` no schema recebe estas frases. O modelo principal
(`change-haircut`) recebe opções fechadas e não passa por aqui.

Há duas formas de instrução, uma para cada família de modelo (a escolha fica em
`planos.perfil_de`):

- `prompt_edicao`, curta, para o FLUX Kontext. Segue o que a documentação de edição dele
  recomenda: dizer o que muda e dizer explicitamente o que deve ficar igual (rosto, pele,
  roupa, fundo). É a instrução do caminho atual e não mudou;
- `prompt_detalhado`, longa, para o Nano Banana (Gemini), que segue bem instruções longas e
  específicas. Organizada por prioridade: a pessoa, a textura (mantida ou escolhida), o
  corte e a cor pedidos, e a naturalidade. A descrição livre vai como foi escrita, com a
  ordem de seguir cada detalhe e de manter local o que é local.

Nenhuma frase garante fidelidade: modelos generativos interpretam o pedido de forma
aproximada, e a qualidade real só se conhece no teste com o serviço
(`scripts/comparar_simulacoes.py`).

A estratégia de idioma (`AI_INSTRUCAO_IDIOMA`) fica em um lugar só:

- `pt_com_termos` (padrão): a descrição vai como foi escrita, em português, e ao lado vão
  os termos técnicos reconhecidos em inglês (`glossario.py`);
- `pt`: a descrição vai só em português, sem os termos.

O gênero do corte, que no modelo principal é o campo `gender`, aqui vira uma frase junto do
corte novo. Na instrução curta (Kontext), "none" não gera frase (é o padrão do modelo); na
detalhada (Nano Banana), "none" é a escolha "Neutro" e gera a frase de corte neutro.
"""

from __future__ import annotations

from typing import Literal

from app.services.ai.glossario import termos_em_ingles
from app.services.ai.pedido import Alteracao, PedidoCapilar

Estrategia = Literal["pt_com_termos", "pt"]

#: O gênero do corte, quando escolhido, na língua da instrução.
GENERO_DO_CORTE = {
    "female": "It is a women's haircut.",
    "male": "It is a men's haircut.",
}

PRESERVAR = (
    "Keep the same person: the face, identity, facial features, skin tone, makeup, "
    "expression, head position, clothing, background and lighting must stay unchanged. "
    "Photorealistic result with natural hair texture and a realistic hairline."
)


def descrever(alteracao: Alteracao, estrategia: Estrategia = "pt_com_termos") -> str:
    """Uma alteração (corte ou cor) como trecho de instrução em inglês."""
    if alteracao.ingles is not None:
        return alteracao.ingles
    # Aspas duplas encerrariam a citação no meio: viram simples.
    texto = alteracao.texto.replace('"', "'")
    if estrategia == "pt":
        return f'"{texto}" (described in Brazilian Portuguese)'
    termos = termos_em_ingles(alteracao.texto, alteracao.campo)
    if not termos:
        return f'"{texto}" (described in Brazilian Portuguese)'
    return f'"{texto}" (described in Brazilian Portuguese; key terms: {", ".join(termos)})'


def prompt_edicao(pedido: PedidoCapilar, estrategia: Estrategia = "pt_com_termos") -> str:
    """Instrução para edição de uma imagem (a foto do cliente) a partir de texto."""
    partes = ["Edit only the hair of the person in this photo."]
    if pedido.corte is not None:
        partes.append(f"New haircut: {descrever(pedido.corte, estrategia)}.")
        if pedido.genero in GENERO_DO_CORTE:
            partes.append(GENERO_DO_CORTE[pedido.genero])
    else:
        partes.append("Keep the current haircut, length and hairstyle exactly as they are.")
    if pedido.cor is not None:
        partes.append(f"New hair color: {descrever(pedido.cor, estrategia)}.")
    else:
        partes.append("Keep the current hair color exactly as it is.")
    # O tipo de cabelo escolhido também vale no Kontext (sem ele, a frase não existe e a
    # instrução é a mesma de antes).
    if pedido.textura is not None:
        partes.append(f"New hair texture: {TEXTURA_EM_INGLES[pedido.textura]}.")
    partes.append(PRESERVAR)
    return " ".join(partes)


#: O que não pode mudar, na instrução detalhada. A lista é explícita porque o que não é
#: citado fica a critério do modelo: rosto "embelezado" ou fundo recriado são erros comuns
#: de edição generativa e, numa prévia de salão, desmentem a simulação.
PRESERVAR_DETALHADO = (
    "Keep everything else exactly as in the original photo: the face and identity, facial "
    "features and proportions, expression, eyes, eyebrows, skin tone and skin texture, "
    "makeup, ears, neck, body, clothing, jewelry and accessories, background, lighting, "
    "camera angle, framing and image proportions. Do not retouch, beautify, slim or age the "
    "face, do not add or remove accessories, and do not add text, logos or borders."
)

#: Como o cabelo novo deve parecer: é o que separa uma prévia crível de uma colagem.
REALISMO_DETALHADO = (
    "Make the hair look real: individual strands, natural texture, a believable hairline "
    "and parting, and hair that falls naturally around the face, ears, neck and shoulders, "
    "with highlights and shadows that match the lighting of the original photo."
)


def descrever_detalhado(alteracao: Alteracao, estrategia: Estrategia = "pt_com_termos") -> str:
    """Uma alteração na instrução detalhada: a descrição completa do catálogo, se houver.

    Texto livre segue como foi escrito, com a mesma estratégia de idioma da instrução curta:
    o detalhe que o profissional escreveu não se perde numa tradução.
    """
    if alteracao.detalhe:
        return alteracao.detalhe
    return descrever(alteracao, estrategia)


def prompt_detalhado_original(pedido: PedidoCapilar, estrategia: Estrategia = "pt_com_termos") -> str:
    """A primeira instrução detalhada (2026-11-05), guardada para comparação.

    Não é mais a da produção: `prompt_detalhado` a substituiu depois do relato de que a
    simulação abria os cachos e aumentava o comprimento. Fica aqui, sem mudança, para que
    `scripts/comparar_simulacoes.py` meça as duas com as mesmas fotos (variante
    "original").
    """
    partes = [
        "Edit this photograph of a real person to preview a new look at a hair salon. "
        "Change only the hair. The result must still look like the same, unedited photo "
        "of the same person."
    ]
    if pedido.corte is not None:
        partes.append(f"New haircut: {descrever_detalhado(pedido.corte, estrategia)}.")
        if pedido.genero in GENERO_DO_CORTE:
            partes.append(GENERO_DO_CORTE[pedido.genero])
    else:
        partes.append(
            "Keep the current haircut exactly as it is: the same length, shape, layers, "
            "parting, fringe and volume. Only the color changes."
        )
    if pedido.cor is not None:
        partes.append(f"New hair color: {descrever_detalhado(pedido.cor, estrategia)}.")
        partes.append(
            "Apply the color realistically, with natural variation in tone and shine along "
            "the strands."
        )
    else:
        partes.append(
            "Keep the current hair color exactly as it is, including highlights, roots and "
            "gray hairs. Only the cut changes."
        )
    partes.append(REALISMO_DETALHADO)
    partes.append(PRESERVAR_DETALHADO)
    return " ".join(partes)


#: Cada tipo de cabelo na língua da instrução. O tipo detalhado diz o tamanho do cacho
#: comparado a objetos comuns, como se faz em salão: é o que diferencia 3A de 3C.
TEXTURA_EM_INGLES = {
    "liso": "straight hair",
    "ondulado": "wavy hair, with S-shaped waves",
    "cacheado": "curly hair, with defined spiral curls",
    "crespo": "coily, afro-textured hair, with tight coils and zigzags",
    "1A": "type 1A straight hair: very fine, completely straight and flat, with little volume",
    "1B": "type 1B straight hair: straight, with a little more body and volume",
    "1C": "type 1C straight hair: straight but thicker and coarser, with a slight tendency to bend",
    "2A": "type 2A wavy hair: loose, open, gentle waves",
    "2B": "type 2B wavy hair: well-defined S-shaped waves",
    "2C": "type 2C wavy hair: deep, voluminous S-shaped waves, close to curls",
    "3A": "type 3A curly hair: large, loose spiral curls, about as wide as a thick marker",
    "3B": "type 3B curly hair: medium, well-defined springy curls, about as wide as a finger",
    "3C": "type 3C curly hair: small, tight, voluminous corkscrew curls, about as wide as a pencil",
    "4A": "type 4A coily hair: small, tightly wound, defined S-shaped coils, about as wide as a knitting needle",
    "4B": "type 4B coily hair: a Z-shaped zigzag pattern with sharp angles and little curl definition, dense",
    "4C": "type 4C coily hair: very tight zigzag coils with very little definition, strong shrinkage and dense volume",
}

#: O gênero do corte na instrução detalhada. "Neutro" (o valor "none" do modelo
#: especializado) é uma escolha da pessoa, e não falta dela: vira uma frase própria.
GENERO_DO_CORTE_DETALHADO = {
    **GENERO_DO_CORTE,
    "none": "It is a gender-neutral haircut, not styled as typically feminine or masculine.",
}

#: Prioridade 1: a pessoa. É o que, se mudar, invalida a prévia inteira.
PESSOA = (
    "Priority 1, the person: keep the same person exactly as in the photo. The face and "
    "identity, facial features and proportions, apparent age, head shape, expression, eyes, "
    "eyebrows, skin tone and skin texture, makeup, ears, neck, body, clothing, jewelry and "
    "accessories, head position, background, lighting, camera angle, framing and image "
    "proportions stay unchanged. Do not retouch, beautify, slim or age the face, and do not "
    "add text, logos or borders."
)

#: A textura natural, quando a pessoa escolhe "Manter meu tipo de cabelo atual". Diz o que
#: manter e, em seguida, os desvios que esse tipo de modelo comete (o relato dos testes:
#: "a IA abriu os meus cachos").
TEXTURA_NATURAL = (
    "the same curl pattern, the same size and tightness of each wave, curl or coil, the "
    "same density, the same volume and the same natural frizz and definition. Straight hair "
    "stays straight; wavy, curly and coily hair keep exactly their own pattern. Do not "
    "loosen, open up, stretch, relax or straighten curls or coils, and do not make them more "
    "uniform, shinier or more defined than they are."
)

#: Descrição livre: tudo o que a pessoa escreveu vale, inclusive onde cada mudança vai.
FIEL_AO_CORTE = (
    "Follow every detail of this description, such as length, fringe, layers, volume, ends "
    "and sides, and keep any part it says to keep. Do not add details that were not asked for."
)
FIEL_A_COR = (
    "Follow every detail of this description, including where each color goes (roots, "
    "lengths, ends, strands around the face, the under-layer or only some highlights) and "
    "any part it says to keep. Keep localized changes local: do not spread them to the "
    "whole hair, and do not add colors that were not asked for."
)

#: Prioridade 4: a naturalidade. Diz como deve parecer, não só o que evitar.
NATURALIDADE = (
    "Priority 4, a real photograph: the result must look like an unedited photo, with "
    "individual strands, a natural hairline and parting, a natural transition between hair "
    "and skin, hair that falls naturally around the face, ears, neck and shoulders, volume "
    "that suits the haircut, color with natural depth, and highlights and shadows that match "
    "the lighting of the original photo. Avoid a wig-like, plastic, painted or overly "
    "uniform look."
)


def _papeis_das_imagens(pedido: PedidoCapilar) -> list[str]:
    """Quem é quem, quando a foto vem acompanhada de referências (só no experimento).

    A pessoa da referência de corte não é a cliente: sem dizer isso, o modelo tende a
    misturar os rostos.
    """
    if not pedido.referencias:
        return []
    frases = ["Image 1 is the client: the only person who may appear in the result."]
    for posicao, papel in enumerate(pedido.referencias, start=2):
        if papel == "corte":
            frases.append(
                f"Image {posicao} is only a haircut reference: take from it the haircut "
                "shape, silhouette, layers, fringe and finish, and nothing else. Do not take "
                "that person's face, skin, identity, hair color, hair texture or clothing."
            )
        else:
            frases.append(
                f"Image {posicao} is a close-up of the client's own natural hair: match its "
                "curl pattern, curl size and texture exactly."
            )
    return frases


def _textura(pedido: PedidoCapilar) -> str:
    """Prioridade 2: a textura do cabelo, mantida ou trocada pela escolhida.

    Manter é uma instrução positiva (preservar o que a foto mostra) e vence qualquer
    menção a outra textura nas descrições. Trocar aplica a textura escolhida no cabelo
    todo; a densidade continua a da foto.
    """
    if pedido.textura is None:
        return (
            "Priority 2, the hair texture: keep the client's natural hair texture exactly as "
            f"in the photo: {TEXTURA_NATURAL} This takes priority over any texture mentioned "
            "in the descriptions below."
        )
    return (
        f"Priority 2, the hair texture: change the hair texture to {TEXTURA_EM_INGLES[pedido.textura]}. "
        "Apply this texture to all of the hair, with a realistic, consistent pattern and the "
        "volume and natural shrinkage this texture has, and keep the same hair density as in "
        "the photo. This chosen texture takes priority over any texture mentioned in the "
        "descriptions below."
    )


def _comprimento(pedido: PedidoCapilar) -> str:
    """O comprimento: o relato dos testes foi "aumentou o comprimento do meu cabelo"."""
    if pedido.corte is None and pedido.textura is None:
        frase = "Keep the current length exactly: the hair must not become longer or shorter."
    elif pedido.corte is None:
        frase = (
            "Keep the current length: the hair is not cut or lengthened. A tighter texture "
            "naturally looks shorter because of shrinkage, and that is expected."
        )
    else:
        frase = (
            "Change the length only as much as the requested haircut requires, and never make "
            "the hair longer than in the photo unless the description explicitly asks for "
            "longer hair."
        )
    return (
        f"{frase} Judge length by how the hair falls in the photo, with its natural shrinkage, "
        "not by its stretched length, and do not turn volume into length."
    )


def _mudanca_pedida(pedido: PedidoCapilar, estrategia: Estrategia) -> str:
    """Prioridade 3: o corte e a cor, cada um só quando foi pedido, e o comprimento."""
    frases = ["Priority 3, the requested change:"]
    textura_do_corte = "the chosen texture" if pedido.textura else "the client's own hair texture"
    if pedido.corte is not None:
        frases.append(f"New haircut: {descrever_detalhado(pedido.corte, estrategia)}.")
        if not pedido.corte.detalhe:
            frases.append(FIEL_AO_CORTE)
        frases.append(GENERO_DO_CORTE_DETALHADO[pedido.genero])
        frases.append(f"Shape this haircut with {textura_do_corte}, the way a stylist would cut it.")
    else:
        frases.append(
            "Keep the current haircut exactly as it is: the same shape, layers, parting and fringe."
        )
    frases.append(_comprimento(pedido))
    if pedido.cor is not None:
        frases.append(f"New hair color: {descrever_detalhado(pedido.cor, estrategia)}.")
        if not pedido.cor.detalhe:
            frases.append(FIEL_A_COR)
        frases.append(
            "Apply the color with natural depth and variation in tone and shine along the "
            "strands. Coloring does not change the curl pattern or the texture set in priority 2."
        )
    else:
        frases.append(
            "Keep the current hair color exactly as it is, including highlights, roots and gray hairs."
        )
    return " ".join(frases)


def prompt_detalhado(pedido: PedidoCapilar, estrategia: Estrategia = "pt_com_termos") -> str:
    """Instrução do Nano Banana, organizada por prioridade.

    1. a pessoa (identidade, rosto, idade aparente, formato da cabeça, fundo, luz,
       enquadramento);
    2. a textura do cabelo: a da foto ("Manter meu tipo de cabelo atual") ou a escolhida
       (liso, ondulado, cacheado, crespo, ou um tipo de 1A a 4C);
    3. a mudança pedida: o corte e a cor, cada um só se foi pedido, com o comprimento; a
       descrição livre vai como foi escrita, com a ordem de seguir cada detalhe e de manter
       local o que é local (mechas só nas pontas não viram mechas no cabelo todo);
    4. a naturalidade da foto.

    A abertura segue o modelo de "máscara semântica" da documentação do Google ("Using the
    provided image, change only the [element]... Keep everything else exactly the same").
    Cada frase depende do pedido, para nenhuma contradizer outra: sem corte, o corte e o
    comprimento ficam; sem cor, a cor fica; a textura escolhida (ou a mantida) vence
    qualquer textura citada nas descrições.
    """
    partes = [
        "Using the provided photo of a real person, change only the hair to preview a new "
        "look at a hair salon, and keep everything else exactly the same. This is an edit of "
        "an existing photograph, not a new image. Follow these priorities in order.",
        *_papeis_das_imagens(pedido),
        PESSOA,
        _textura(pedido),
        _mudanca_pedida(pedido, estrategia),
        NATURALIDADE,
    ]
    return " ".join(partes)
