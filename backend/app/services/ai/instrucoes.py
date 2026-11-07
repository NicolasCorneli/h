"""Instrução enviada ao modelo de edição por texto (`prompt`).

Só o modelo que tem o campo `prompt` no schema recebe estas frases. O modelo principal
(`change-haircut`) recebe opções fechadas e não passa por aqui.

Há duas formas de instrução, uma para cada família de modelo (a escolha fica em
`planos.perfil_de`):

- `prompt_edicao`, curta, para o FLUX Kontext. Segue o que a documentação de edição dele
  recomenda: dizer o que muda e dizer explicitamente o que deve ficar igual (rosto, pele,
  roupa, fundo). É a instrução do caminho atual e não mudou;
- `prompt_detalhado`, longa, para o Nano Banana (Gemini), que segue bem instruções longas e
  específicas. Diz o contexto (prévia de salão), o corte e a cor com a descrição completa
  do catálogo, como o cabelo deve parecer, e lista um a um os elementos que não podem
  mudar, inclusive retoques no rosto, que esse tipo de modelo às vezes faz sem que se peça.

Nenhuma frase garante fidelidade: modelos generativos interpretam o pedido de forma
aproximada, e a qualidade real só se conhece no teste com o serviço
(`scripts/comparar_simulacoes.py`).

A estratégia de idioma (`AI_INSTRUCAO_IDIOMA`) fica em um lugar só:

- `pt_com_termos` (padrão): a descrição vai como foi escrita, em português, e ao lado vão
  os termos técnicos reconhecidos em inglês (`glossario.py`);
- `pt`: a descrição vai só em português, sem os termos.

O gênero do corte, que no modelo principal é o campo `gender`, aqui vira uma frase junto do
corte novo. Sem gênero escolhido ("none"), a instrução é a mesma de antes da opção existir.
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
    termos = termos_em_ingles(alteracao.texto)
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


#: Cada padrão de curvatura na língua da instrução. O tipo detalhado diz o tamanho do
#: cacho comparado a objetos comuns, como se faz em salão: é o que diferencia 3A de 3C, e
#: é exatamente a medida que o modelo tende a perder (abrindo cachos fechados).
CURVATURA_EM_INGLES = {
    "liso": "straight hair",
    "ondulado": "wavy hair, with S-shaped waves",
    "cacheado": "curly hair, with defined spiral curls",
    "crespo": "coily, afro-textured hair, with very tight coils and zigzags",
    "1A": "straight hair (type 1A): fine, completely straight strands with no bend",
    "1B": "straight hair (type 1B): straight, with a little body and a slight bend at the ends",
    "1C": "straight hair (type 1C): straight but coarse, with a slight bend and some volume",
    "2A": "wavy hair (type 2A): loose, gentle S-shaped waves lying close to the head",
    "2B": "wavy hair (type 2B): defined S-shaped waves that start around mid-length",
    "2C": "wavy hair (type 2C): strong S-shaped waves from the roots, close to loose curls",
    "3A": "curly hair (type 3A): large, loose spiral curls about as wide as a thick marker",
    "3B": "curly hair (type 3B): springy ringlets about as wide as a finger",
    "3C": "curly hair (type 3C): tight corkscrew curls about as wide as a pencil, dense and voluminous",
    "4A": "coily hair (type 4A): tight S-shaped coils about as wide as a knitting needle, dense",
    "4B": "coily hair (type 4B): very tight Z-shaped zigzag coils with little visible curl definition, dense",
    "4C": "coily hair (type 4C): extremely tight zigzag coils with very little definition, strong shrinkage and dense volume",
}

#: Prioridade 1: a pessoa. É o que, se mudar, invalida a prévia inteira.
PESSOA = (
    "Priority 1, the person: keep the same person exactly as in the photo. The face and "
    "identity, facial features and proportions, expression, eyes, eyebrows, skin tone and "
    "skin texture, makeup, ears, neck, body, clothing, jewelry and accessories, head "
    "position, background, lighting, camera angle, framing and image proportions stay "
    "unchanged. Do not retouch, beautify, slim or age the face, and do not add text, logos "
    "or borders."
)

#: Prioridade 2: a textura natural. Responde ao relato dos testes ("a IA abriu os meus
#: cachos"): diz o que manter e, em seguida, os desvios que esse tipo de modelo comete.
TEXTURA_NATURAL = (
    "Keep the natural texture of the hair in the photo: the same curl pattern, the same "
    "size and tightness of each wave, curl or coil, the same density, the same volume and "
    "the same natural frizz and definition. Straight hair stays straight; wavy, curly and "
    "coily hair keep exactly their own pattern. Do not loosen, open up, stretch, relax or "
    "straighten curls or coils, and do not make them more uniform, shinier or more defined "
    "than they are."
)

#: Prioridade 4: a naturalidade. Diz como deve parecer, não só o que evitar.
NATURALIDADE = (
    "Priority 4, a real photograph: the result must look like an unedited photo, with "
    "individual strands, a believable hairline and parting, hair that falls naturally "
    "around the face, ears, neck and shoulders, and highlights and shadows that match the "
    "lighting of the original photo. Avoid a wig-like, painted or overly uniform look."
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


def _cabelo_natural(pedido: PedidoCapilar) -> str:
    """Prioridade 2: o que é do cabelo da cliente e não muda com o pedido."""
    frases = ["Priority 2, the client's natural hair: the result keeps the client's own hair.", TEXTURA_NATURAL]
    if pedido.corte is not None:
        # Sem esta exceção, "manter a textura" contradiria um pedido de escova ou de
        # permanente, e o modelo teria de escolher qual instrução desobedecer.
        frases.append(
            "The only exception is a requested haircut that explicitly asks for a different "
            "texture (for example straightened, blow-dried, permed or curled): then apply "
            "that texture."
        )
    if pedido.curvatura is not None:
        frases.append(
            f"The client describes their natural hair as {CURVATURA_EM_INGLES[pedido.curvatura]}. "
            "Use this to read the curl pattern in the photo; the photo remains the main reference."
        )
    if pedido.corte is None:
        frases.append("Keep the current length exactly: the hair must not become longer or shorter.")
    else:
        frases.append(
            "Change the length only as much as the requested haircut requires, and never make "
            "the hair longer than in the photo unless the requested haircut explicitly asks "
            "for longer hair."
        )
    frases.append(
        "Judge length by how the hair falls in the photo, with its natural shrinkage, not by "
        "its stretched length, and do not turn volume into length."
    )
    return " ".join(frases)


def _mudanca_pedida(pedido: PedidoCapilar, estrategia: Estrategia) -> str:
    """Prioridade 3: o corte e a cor pedidos, cada um só quando foi pedido."""
    frases = ["Priority 3, the requested change:"]
    if pedido.corte is not None:
        frases.append(f"New haircut: {descrever_detalhado(pedido.corte, estrategia)}.")
        if pedido.genero in GENERO_DO_CORTE:
            frases.append(GENERO_DO_CORTE[pedido.genero])
        frases.append(
            "Shape this haircut with the client's own hair texture, the way a stylist would "
            "cut this kind of hair."
        )
    else:
        frases.append(
            "Keep the current haircut exactly as it is: the same shape, layers, parting and fringe."
        )
    if pedido.cor is not None:
        frases.append(f"New hair color: {descrever_detalhado(pedido.cor, estrategia)}.")
        frases.append(
            "Apply the color with natural variation in tone and shine along the strands, "
            "without changing the curl pattern or the texture."
        )
    else:
        frases.append(
            "Keep the current hair color exactly as it is, including highlights, roots and gray hairs."
        )
    return " ".join(frases)


def prompt_detalhado(pedido: PedidoCapilar, estrategia: Estrategia = "pt_com_termos") -> str:
    """Instrução do Nano Banana, organizada por prioridade.

    1. a pessoa (identidade, rosto, fundo, luz, enquadramento);
    2. o cabelo natural da cliente (curvatura, textura, densidade, volume e comprimento),
       com a curvatura informada como apoio à leitura da foto;
    3. a mudança pedida (corte e cor, cada um só se foi pedido);
    4. a naturalidade da foto.

    A abertura segue o modelo de "máscara semântica" da documentação do Google ("Using the
    provided image, change only the [element]... Keep everything else exactly the same").
    Cada frase depende do pedido: sem corte, o comprimento e o corte ficam como estão; sem
    cor, a cor fica; o pedido de outra textura (escova, permanente) é a única exceção à
    preservação da curvatura, para que nenhuma frase contradiga outra.
    """
    partes = [
        "Using the provided photo of a real person, change only the hair to preview a new "
        "look at a hair salon, and keep everything else exactly the same. Follow these "
        "priorities in order.",
        *_papeis_das_imagens(pedido),
        PESSOA,
        _cabelo_natural(pedido),
        _mudanca_pedida(pedido, estrategia),
        NATURALIDADE,
    ]
    return " ".join(partes)
