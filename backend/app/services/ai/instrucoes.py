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


def prompt_detalhado(pedido: PedidoCapilar, estrategia: Estrategia = "pt_com_termos") -> str:
    """Instrução longa e específica, para modelos que seguem instruções detalhadas."""
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
