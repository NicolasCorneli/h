"""Provedor local, sem IA e sem custo: padrão em desenvolvimento e nos testes.

Serve para três coisas: desenvolver sem credencial, rodar a suíte de testes sem rede e
demonstrar o sistema inteiro quando não houver chave do provedor real.

**Não é inteligência artificial.** Ele recolore os pixels escuros (que em um retrato
correspondem, em boa parte, ao cabelo) na direção da cor pedida e escreve um aviso na
imagem, justamente para que ninguém confunda o resultado com o do modelo de verdade. O
corte não muda.

A escolha do modelo (`preparar`) segue as mesmas regras do provedor real, sem o schema ao
vivo: assim a prévia do pedido e os testes enxergam o mesmo plano que a Replicate receberia.
"""

from __future__ import annotations

import io
import time

import numpy as np
from PIL import Image, ImageDraw

from app.core.config import obter_config
from app.services.ai.base import EntradaSimulacao, ProvedorIA, SaidaSimulacao
from app.services.ai.pedido import PedidoCapilar
from app.services.ai.planos import Plano, configuracao_de, planejar
from app.services.catalogo import opcao_de_cor

LIMIAR_ESCURO = 110
AVISO = "simulação local, sem IA"
#: Usada quando a cor descrita não é uma das cores do catálogo.
AMOSTRA_PADRAO = "#7A5230"


def _cor_rgb(amostra: str) -> tuple[int, int, int]:
    texto = amostra.lstrip("#")
    return tuple(int(texto[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


class ProvedorLocal(ProvedorIA):
    nome = "fake"
    modelo = "provedor local (sem IA)"

    def preparar(self, pedido: PedidoCapilar) -> Plano:
        return planejar(pedido, configuracao_de(obter_config()))

    def gerar(self, entrada: EntradaSimulacao) -> SaidaSimulacao:
        inicio = time.monotonic()
        plano = self.preparar(entrada.pedido)
        with Image.open(io.BytesIO(entrada.imagem)) as original:
            imagem = original.convert("RGB")

        if entrada.pedido.cor is not None:
            opcao = opcao_de_cor(entrada.pedido.cor.texto)
            amostra = opcao.amostra if opcao and opcao.amostra else AMOSTRA_PADRAO
            matriz = np.array(imagem).astype(np.float32)
            luminancia = matriz.mean(axis=2)
            # Máscara suave: quanto mais escuro o pixel, mais ele recebe a cor escolhida.
            peso = np.clip((LIMIAR_ESCURO - luminancia) / LIMIAR_ESCURO, 0, 1)[:, :, None]
            destino = np.array(_cor_rgb(amostra), dtype=np.float32)
            matriz = matriz * (1 - peso * 0.85) + destino * (peso * 0.85)
            imagem = Image.fromarray(np.clip(matriz, 0, 255).astype(np.uint8))

        desenho = ImageDraw.Draw(imagem)
        largura, altura = imagem.size
        desenho.rectangle([0, altura - 34, largura, altura], fill=(27, 23, 20))
        legenda = f"{AVISO} · {entrada.pedido.rotulo_corte[:40]}"
        desenho.text((12, altura - 25), legenda, fill=(243, 237, 231))

        saida = io.BytesIO()
        imagem.save(saida, format="JPEG", quality=90)
        return SaidaSimulacao(
            imagem=saida.getvalue(),
            mime="image/jpeg",
            modelo=self.modelo,
            tempo_ms=int((time.monotonic() - inicio) * 1000),
            instrucao=plano.instrucao,
        )
