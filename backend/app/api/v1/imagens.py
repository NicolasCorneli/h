"""Entrega das imagens por URL assinada.

Esta é a única rota sem cabeçalho `Authorization`, e por um motivo técnico: o componente
`<Image>` do React Native não envia cabeçalhos. A autorização, aqui, é a assinatura HMAC
da query — emitida por este servidor, ligada a uma imagem e a um dono, válida por poucos
minutos. Sem assinatura válida, a resposta é 404.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response
from fastapi.responses import RedirectResponse

from app.core.dependencies import SessaoDep
from app.services import imagens as servico

router = APIRouter(prefix="/imagens", tags=["imagens"])


@router.get("/{imagem_id}", response_class=Response)
def entregar(
    imagem_id: uuid.UUID,
    sessao: SessaoDep,
    t: Annotated[str, Query(max_length=200, description="assinatura temporária")],
) -> Response:
    conteudo, mime, url_externa = servico.entregar(sessao, imagem_id, t)
    if url_externa:
        return RedirectResponse(url_externa, status_code=307)
    return Response(
        content=conteudo,
        media_type=mime,
        # `private` porque a imagem é de uma pessoa: nenhum intermediário deve guardá-la.
        headers={"Cache-Control": "private, max-age=300"},
    )
