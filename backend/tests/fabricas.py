"""Imagens sintéticas para os testes.

`retrato_valido()` é um desenho que a cascata de Haar reconhece como rosto frontal, o que
permite exercitar o caminho aprovado da validação sem usar a fotografia de pessoa alguma.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def retrato_valido(largura: int = 720, altura: int = 960) -> bytes:
    imagem = Image.new("RGB", (largura, altura), (205, 196, 188))
    desenho = ImageDraw.Draw(imagem)
    cx, cy = largura // 2, int(altura * 0.40)
    fw, fh = int(largura * 0.26), int(altura * 0.20)

    desenho.ellipse([cx - fw - 26, cy - fh - 70, cx + fw + 26, cy + fh * 0.4], fill=(52, 38, 30))
    desenho.ellipse([cx - fw, cy - fh, cx + fw, cy + int(fh * 1.5)], fill=(222, 186, 160))
    desenho.ellipse(
        [cx - fw * 0.8, cy - fh * 0.95, cx + fw * 0.8, cy - fh * 0.1], fill=(231, 197, 172)
    )

    olho_y = cy - int(fh * 0.10)
    desenho.rectangle(
        [cx - int(fw * 0.95), olho_y - int(fh * 0.22), cx + int(fw * 0.95), olho_y + int(fh * 0.12)],
        fill=(176, 143, 122),
    )
    desenho.rectangle(
        [cx - int(fw * 0.13), olho_y - int(fh * 0.24), cx + int(fw * 0.13), olho_y + int(fh * 0.55)],
        fill=(236, 203, 178),
    )
    for lado in (-1, 1):
        ox = cx + lado * int(fw * 0.45)
        desenho.ellipse(
            [ox - int(fw * 0.22), olho_y - int(fh * 0.11), ox + int(fw * 0.22), olho_y + int(fh * 0.09)],
            fill=(242, 238, 233),
        )
        desenho.ellipse(
            [ox - int(fw * 0.09), olho_y - int(fh * 0.07), ox + int(fw * 0.09), olho_y + int(fh * 0.07)],
            fill=(46, 34, 26),
        )
        desenho.rectangle(
            [ox - int(fw * 0.26), olho_y - int(fh * 0.26), ox + int(fw * 0.26), olho_y - int(fh * 0.17)],
            fill=(70, 50, 38),
        )
        maca_rosto = cx + lado * int(fw * 0.55)
        desenho.ellipse(
            [maca_rosto - int(fw * 0.3), olho_y + int(fh * 0.18), maca_rosto + int(fw * 0.3), olho_y + int(fh * 0.62)],
            fill=(233, 199, 174),
        )
    desenho.rectangle(
        [cx - int(fw * 0.30), cy + int(fh * 0.85), cx + int(fw * 0.30), cy + int(fh * 0.98)],
        fill=(158, 96, 86),
    )

    imagem = imagem.filter(ImageFilter.GaussianBlur(2.0))
    matriz = np.array(imagem).astype(np.int16)
    matriz += np.random.default_rng(7).integers(-7, 8, matriz.shape, dtype=np.int16)
    saida = io.BytesIO()
    Image.fromarray(np.clip(matriz, 0, 255).astype(np.uint8)).save(saida, format="JPEG", quality=92)
    return saida.getvalue()


def imagem_lisa(largura: int = 720, altura: int = 960, tom: int = 160) -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", (largura, altura), (tom, tom, tom)).save(saida, format="JPEG")
    return saida.getvalue()


def arquivo_de_foto(conteudo: bytes | None = None) -> dict[str, tuple[str, bytes, str]]:
    return {"foto": ("retrato.jpg", conteudo or retrato_valido(), "image/jpeg")}
