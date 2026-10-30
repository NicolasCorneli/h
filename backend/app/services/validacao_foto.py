"""Validação da fotografia no servidor, antes de qualquer chamada paga (seção 16).

O aplicativo já checa dimensão e enquadramento, mas aquilo é conveniência de interface:
a decisão de gastar uma inferência é do servidor. As checagens aqui são as mesmas que o
pré-projeto descreve (resolução, proporção, luminância, enquadramento/rosto) e rodam na
ordem do mais barato para o mais caro.

A imagem aprovada é **re-codificada em JPEG**, o que remove metadados EXIF — inclusive
coordenadas de GPS que a câmera possa ter embutido. É minimização de dados na prática:
nada além dos pixels necessários chega ao provedor.
"""

from __future__ import annotations

import io
import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from app.core.config import obter_config
from app.core.erros import FotoRecusada

log = logging.getLogger(__name__)

#: Barreira contra "bomba de descompressão": arquivo pequeno que decodifica em bilhões
#: de pixels. 50 MP cobre com folga qualquer câmera de celular.
Image.MAX_IMAGE_PIXELS = 50_000_000

FORMATOS_ACEITOS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@dataclass(frozen=True)
class Problema:
    titulo: str
    detalhe: str

    def como_json(self) -> dict[str, str]:
        return {"titulo": self.titulo, "detalhe": self.detalhe}


@dataclass(frozen=True)
class FotoValidada:
    conteudo: bytes
    mime: str
    largura: int
    altura: int


def _recusar(problemas: list[Problema]) -> None:
    raise FotoRecusada(
        problemas[0].titulo,
        detalhes=[problema.como_json() for problema in problemas],
    )


#: O classificador do OpenCV é um só e não suporta uso simultâneo. A validação da foto e a
#: conferência do enquadramento (que a câmera faz várias vezes por segundo) rodam em
#: threads diferentes do servidor: sem a trava, uma detecção ao mesmo tempo que outra
#: derrubava o processo ou deixava de achar o rosto de uma foto válida. Cada detecção leva
#: milissegundos numa imagem de 640 px, então elas passam uma de cada vez.
_TRAVA_DO_CLASSIFICADOR = threading.Lock()

#: A primeira importação do OpenCV põe o módulo em `sys.modules` antes de terminar de
#: montá-lo (`cv2.data` entra depois). Outra thread que importasse nesse meio tempo recebia
#: o módulo incompleto e caía com "module 'cv2' has no attribute 'data'": acontecia nas
#: primeiras detecções simultâneas depois de o servidor subir.
_TRAVA_DA_IMPORTACAO = threading.Lock()


def _opencv():
    """O módulo `cv2`, sempre inteiro: a importação passa por uma trava."""
    with _TRAVA_DA_IMPORTACAO:
        import cv2
    return cv2


@lru_cache
def _classificador_de_rosto():
    cv2 = _opencv()
    caminho = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    classificador = cv2.CascadeClassifier(str(caminho))
    if classificador.empty():
        raise RuntimeError(f"classificador de rosto não carregado: {caminho}")
    return classificador


def _rostos(imagem: Image.Image, tamanho_minimo: int = 60) -> list[tuple[float, float, float, float]]:
    """Rostos frontais encontrados, como (x, y, largura, altura) na escala da imagem dada."""
    cv2 = _opencv()

    cinza = np.array(imagem.convert("L"))
    # Reduz para acelerar: 640 px no maior lado é suficiente para a cascata.
    escala = 640 / max(cinza.shape)
    if escala < 1:
        cinza = cv2.resize(cinza, (int(cinza.shape[1] * escala), int(cinza.shape[0] * escala)))
    else:
        escala = 1.0
    cinza = cv2.equalizeHist(cinza)
    with _TRAVA_DO_CLASSIFICADOR:
        encontrados = _classificador_de_rosto().detectMultiScale(
            cinza, scaleFactor=1.1, minNeighbors=4, minSize=(tamanho_minimo, tamanho_minimo)
        )
    return [(x / escala, y / escala, w / escala, h / escala) for (x, y, w, h) in encontrados]


def tem_rosto(imagem: Image.Image) -> bool:
    """Detecção frontal por cascata de Haar: roda local, sem enviar nada para fora."""
    return len(_rostos(imagem)) > 0


#: Região do quadro onde o centro do rosto precisa estar para contar como "dentro do
#: guia", em frações da largura e da altura. É uma aproximação do guia oval da tela: a
#: prévia da câmera corta as bordas da foto de jeitos diferentes em cada aparelho.
REGIAO_DO_GUIA = (0.2, 0.8, 0.12, 0.75)
#: Abaixo disso o rosto está longe demais para uma boa simulação.
LARGURA_MINIMA_DO_ROSTO = 0.15
#: Teto da miniatura enviada pela tela da câmera.
MAX_BYTES_ENQUADRAMENTO = 2 * 1024 * 1024


def rosto_no_guia(conteudo: bytes) -> bool:
    """O quadro tem um rosto de frente, centralizado e perto o bastante?

    Usado pela tela da câmera, várias vezes por segundo, com uma miniatura. Nada é
    guardado: a imagem só existe durante esta função.
    """
    if not conteudo or len(conteudo) > MAX_BYTES_ENQUADRAMENTO:
        return False
    try:
        aberta = Image.open(io.BytesIO(conteudo))
        # A miniatura da câmera tem poucas centenas de pixels. Dimensão maior que a de
        # qualquer foto aceita não é miniatura: recusada sem decodificar.
        if max(aberta.size) > obter_config().imagem_max_lado:
            return False
        imagem = ImageOps.exif_transpose(aberta)
        imagem.load()
    except Exception:  # noqa: BLE001 - qualquer arquivo ilegível é "sem rosto"
        return False
    largura, altura = imagem.size
    if min(largura, altura) < 120:
        return False
    x_min, x_max, y_min, y_max = REGIAO_DO_GUIA
    minimo = max(24, int(min(largura, altura) * 0.12))
    for x, y, w, h in _rostos(imagem, tamanho_minimo=min(60, minimo)):
        cx, cy = (x + w / 2) / largura, (y + h / 2) / altura
        if x_min <= cx <= x_max and y_min <= cy <= y_max and w / largura >= LARGURA_MINIMA_DO_ROSTO:
            return True
    return False


def ler_envio(arquivo) -> bytes:
    """Lê o arquivo enviado até um byte além do limite, e não mais.

    O limite de corpo da borda olha o `Content-Length`, que um envio em partes (chunked)
    não traz. Ler tudo para a memória antes de medir deixava uma conta autenticada ocupar
    a memória do servidor com um arquivo de qualquer tamanho. Um byte a mais basta para
    `validar_e_normalizar` saber que passou do limite.
    """
    return arquivo.read(obter_config().imagem_max_bytes + 1)


def validar_e_normalizar(conteudo: bytes, *, validar_rosto: bool | None = None) -> FotoValidada:
    config = obter_config()
    problemas: list[Problema] = []

    if not conteudo:
        _recusar([Problema("Arquivo vazio", "Nenhuma imagem foi recebida.")])

    if len(conteudo) > config.imagem_max_bytes:
        limite_mb = config.imagem_max_bytes / (1024 * 1024)
        # A leitura para um byte depois do limite (`ler_envio`): o tamanho real não é
        # conhecido, só que passou.
        _recusar(
            [
                Problema(
                    "Arquivo muito grande",
                    f"O limite é {limite_mb:.0f} MB, e esta imagem passa disso. "
                    "Envie uma foto menor.",
                )
            ]
        )

    # O tipo real vem da decodificação, nunca do nome ou do cabeçalho enviado.
    formato = ""
    dimensoes = (0, 0)
    try:
        with Image.open(io.BytesIO(conteudo)) as inspecao:
            formato = inspecao.format or ""
            dimensoes = inspecao.size
            inspecao.verify()
    # `DecompressionBombError` não herda de OSError nem de ValueError: sem citá-la aqui,
    # a barreira de pixels funciona, mas a recusa sai como erro interno em vez de 422.
    except (UnidentifiedImageError, OSError, ValueError, DecompressionBombError):
        _recusar(
            [
                Problema(
                    "Arquivo não é uma imagem válida",
                    "Envie uma foto em JPEG, PNG ou WebP.",
                )
            ]
        )

    if formato not in FORMATOS_ACEITOS:
        _recusar(
            [
                Problema(
                    "Formato não aceito",
                    f"Formato {formato or 'desconhecido'}. Use JPEG, PNG ou WebP.",
                )
            ]
        )

    # As dimensões vêm do cabeçalho, sem decodificar: uma foto de 8 MB pode ter 50 MP, e
    # decodificá-la inteira só para descobrir que passa do limite ocupava ~150 MB de
    # memória por requisição.
    if max(dimensoes) > config.imagem_max_lado:
        _recusar(
            [
                Problema(
                    "Imagem muito grande",
                    f"O maior lado tem {max(dimensoes)} px; o limite é {config.imagem_max_lado} px.",
                )
            ]
        )

    with Image.open(io.BytesIO(conteudo)) as original:
        # Respeita a orientação do EXIF antes de descartá-lo.
        imagem = ImageOps.exif_transpose(original).convert("RGB")

    largura, altura = imagem.size
    menor_lado, maior_lado = min(largura, altura), max(largura, altura)

    if menor_lado < config.imagem_min_lado:
        problemas.append(
            Problema(
                "Resolução baixa",
                f"A foto tem {menor_lado} px no menor lado; o mínimo é "
                f"{config.imagem_min_lado} px para o recorte do cabelo não sair serrilhado.",
            )
        )
    if maior_lado > config.imagem_max_lado:
        problemas.append(
            Problema(
                "Imagem muito grande",
                f"O maior lado tem {maior_lado} px; o limite é {config.imagem_max_lado} px.",
            )
        )
    if altura > 0 and largura / altura > config.imagem_proporcao_max:
        problemas.append(
            Problema(
                "Enquadramento deitado",
                "Use uma foto em retrato, com o rosto ocupando o centro do quadro.",
            )
        )

    luminancia = float(np.array(imagem.convert("L")).mean())
    if luminancia < config.imagem_luminancia_min:
        problemas.append(
            Problema(
                "Imagem muito escura",
                "Não dá para separar o cabelo do fundo. Aumente a luz de frente.",
            )
        )
    elif luminancia > config.imagem_luminancia_max:
        problemas.append(
            Problema(
                "Imagem muito clara",
                "A foto está estourada de luz e perde o contorno do cabelo.",
            )
        )

    conferir_rosto = config.validar_rosto if validar_rosto is None else validar_rosto
    if conferir_rosto and not problemas and not tem_rosto(imagem):
        problemas.append(
            Problema(
                "Rosto não identificado",
                "Vire para frente e reenquadre o rosto dentro do guia, com o cabelo visível.",
            )
        )

    if problemas:
        log.info(
            "foto recusada: %s", ", ".join(problema.titulo for problema in problemas)
        )
        _recusar(problemas)

    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=90, optimize=True)
    return FotoValidada(
        conteudo=saida.getvalue(), mime="image/jpeg", largura=largura, altura=altura
    )
