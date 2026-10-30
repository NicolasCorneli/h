"""Instrução enviada ao modelo de edição por texto (`prompt`).

Só o modelo que tem o campo `prompt` no schema recebe estas frases. O modelo principal
(`change-haircut`) recebe opções fechadas e não passa por aqui.

As frases seguem o que a documentação de edição do FLUX Kontext recomenda: dizer o que
muda e dizer explicitamente o que deve ficar igual (rosto, pele, roupa, fundo). Nenhuma
frase garante fidelidade: modelos generativos interpretam o pedido de forma aproximada, e a
qualidade real só se conhece no teste com o serviço.

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
