"""Validação da foto no servidor — a barreira que antecede a chamada paga."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from PIL import Image

from app.core.erros import FotoRecusada
from app.services.validacao_foto import tem_rosto, validar_e_normalizar
from tests.fabricas import imagem_lisa, retrato_valido


def titulos(erro: FotoRecusada) -> list[str]:
    return [detalhe["titulo"] for detalhe in erro.detalhes]


def test_retrato_valido_e_aprovado_e_normalizado():
    resultado = validar_e_normalizar(retrato_valido())
    assert resultado.mime == "image/jpeg"
    assert (resultado.largura, resultado.altura) == (720, 960)
    assert resultado.conteudo[:2] == b"\xff\xd8"


def test_rosto_detectado_no_retrato():
    with Image.open(io.BytesIO(retrato_valido())) as imagem:
        assert tem_rosto(imagem) is True


def test_sem_rosto_e_recusado():
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(imagem_lisa())
    assert "Rosto não identificado" in titulos(erro.value)


def test_imagem_lisa_passa_quando_rosto_nao_e_exigido():
    resultado = validar_e_normalizar(imagem_lisa(), validar_rosto=False)
    assert resultado.largura == 720


def test_resolucao_baixa_e_proporcao_deitada():
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(imagem_lisa(largura=640, altura=300))
    assert titulos(erro.value) == ["Resolução baixa", "Enquadramento deitado"]


def test_imagem_escura():
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(imagem_lisa(tom=5))
    assert "Imagem muito escura" in titulos(erro.value)


def test_imagem_estourada():
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(imagem_lisa(tom=250))
    assert "Imagem muito clara" in titulos(erro.value)


def test_arquivo_que_nao_e_imagem():
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(b"%PDF-1.7 nao sou imagem")
    assert "Arquivo não é uma imagem válida" in titulos(erro.value)


def test_arquivo_vazio():
    with pytest.raises(FotoRecusada):
        validar_e_normalizar(b"")


def test_formato_recusado():
    """GIF decodifica, mas não está entre os formatos aceitos."""
    buffer = io.BytesIO()
    Image.new("RGB", (720, 960), (150, 150, 150)).save(buffer, format="GIF")
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(buffer.getvalue())
    assert "Formato não aceito" in titulos(erro.value)


def test_arquivo_acima_do_limite():
    enorme = b"\xff\xd8" + b"\x00" * (9 * 1024 * 1024)
    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(enorme)
    assert "Arquivo muito grande" in titulos(erro.value)


def test_png_e_convertido_para_jpeg():
    buffer = io.BytesIO()
    Image.new("RGB", (720, 960), (150, 150, 150)).save(buffer, format="PNG")
    resultado = validar_e_normalizar(buffer.getvalue(), validar_rosto=False)
    assert resultado.mime == "image/jpeg"


def test_metadados_exif_sao_descartados():
    """Minimização de dados: o que sai daqui não leva data, modelo de câmera nem GPS."""
    original = Image.new("RGB", (720, 960), (150, 150, 150))
    exif = original.getexif()
    exif[271] = "FabricanteTeste"  # Make
    exif[306] = "2026:01:01 10:00:00"  # DateTime
    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", exif=exif)

    entrada = Image.open(io.BytesIO(buffer.getvalue()))
    assert dict(entrada.getexif())  # a entrada realmente tinha metadados

    resultado = validar_e_normalizar(buffer.getvalue(), validar_rosto=False)
    saida = Image.open(io.BytesIO(resultado.conteudo))
    assert not dict(saida.getexif())


def png_que_declara_dimensoes_enormes(largura: int, altura: int) -> bytes:
    """Arquivo minúsculo que diz ser gigante — a clássica "bomba de descompressão".

    O cabeçalho do PNG é montado à mão: 68 bytes que anunciam centenas de milhões de
    pixels. Quem decodificar sem conferir o cabeçalho tenta alocar a imagem inteira.
    """
    import struct
    import zlib

    def pedaco(tipo: bytes, dados: bytes) -> bytes:
        return (
            struct.pack(">I", len(dados))
            + tipo
            + dados
            + struct.pack(">I", zlib.crc32(tipo + dados))
        )

    cabecalho = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + pedaco(b"IHDR", cabecalho)
        + pedaco(b"IDAT", zlib.compress(b"\x00" * 10))
        + pedaco(b"IEND", b"")
    )


def test_bomba_de_descompressao_e_recusada_como_foto_invalida():
    """Recusar não basta: tem de recusar *como foto inválida*, não explodindo.

    A barreira de pixels do Pillow existe e funciona, mas a exceção que ela levanta
    (`DecompressionBombError`) não é `OSError` nem `ValueError`. Se o validador não a
    tratar, um arquivo de 68 bytes vira erro interno em vez de recusa.
    """
    bomba = png_que_declara_dimensoes_enormes(30_000, 30_000)
    assert len(bomba) < 1024, "o arquivo precisa ser minúsculo para o teste fazer sentido"

    with pytest.raises(FotoRecusada) as erro:
        validar_e_normalizar(bomba, validar_rosto=False)
    assert "Arquivo não é uma imagem válida" in titulos(erro.value)


def test_deteccao_de_rosto_simultanea_nao_falha_nem_derruba_o_processo():
    """A validação da foto e a conferência do enquadramento rodam ao mesmo tempo em
    threads diferentes do servidor (a câmera confere o enquadramento várias vezes por
    segundo). O classificador do OpenCV é um só, e não aguenta uso simultâneo: sem a trava,
    o processo caía (falha de segmentação) ou deixava de achar o rosto de uma foto válida.

    Roda num processo à parte para que uma queda vire falha deste teste, e não da suíte.
    """
    roteiro = textwrap.dedent(
        """
        import io
        from concurrent.futures import ThreadPoolExecutor

        import numpy as np
        from PIL import Image

        from app.services.validacao_foto import rosto_no_guia, tem_rosto
        from tests.fabricas import retrato_valido

        retrato = Image.open(io.BytesIO(retrato_valido())).convert("RGB")
        quadro = io.BytesIO()
        Image.fromarray(np.full((480, 360, 3), (0, 140, 0), dtype=np.uint8)).save(quadro, format="JPEG")

        falsos = 0
        with ThreadPoolExecutor(max_workers=8) as pool:
            for _ in range(40):
                validacoes = [pool.submit(tem_rosto, retrato) for _ in range(4)]
                enquadramentos = [pool.submit(rosto_no_guia, quadro.getvalue()) for _ in range(4)]
                falsos += [v.result() for v in validacoes].count(False)
                [e.result() for e in enquadramentos]
        print(falsos)
        """
    )
    resultado = subprocess.run(
        [sys.executable, "-c", roteiro],
        cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert resultado.returncode == 0, f"o processo caiu (código {resultado.returncode}): {resultado.stderr[-300:]}"
    assert resultado.stdout.strip() == "0", f"foto válida recusada sob concorrência: {resultado.stdout}"
