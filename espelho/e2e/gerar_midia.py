"""Gera as mídias de teste do roteiro e2e/fotos-e-camera.mjs numa pasta temporária.

- camera-com-rosto.mjpeg: vídeo para a câmera falsa do Chromium, com um rosto
  centralizado (o mesmo retrato sintético dos testes do servidor);
- foto-grande.jpg: foto de 4000x4000 com ruído (cerca de 18 MB), maior que o limite de
  envio do servidor, como a de um celular atual.

Uso: backend/.venv/bin/python espelho/e2e/gerar_midia.py <pasta>
"""

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(RAIZ))
from tests.fabricas import retrato_valido  # noqa: E402

destino = Path(sys.argv[1])
destino.mkdir(parents=True, exist_ok=True)

rosto = Image.open(io.BytesIO(retrato_valido(640, 853))).resize((360, 480))
quadro = Image.new("RGB", (640, 480), (205, 196, 188))
quadro.paste(rosto, (140, 0))
saida = io.BytesIO()
quadro.save(saida, format="JPEG", quality=90)
(destino / "camera-com-rosto.mjpeg").write_bytes(saida.getvalue() * 30)

ruido = np.random.default_rng(1).integers(0, 255, (4000, 4000, 3), dtype=np.uint8)
Image.fromarray(ruido).save(destino / "foto-grande.jpg", format="JPEG", quality=95)
print(destino)
