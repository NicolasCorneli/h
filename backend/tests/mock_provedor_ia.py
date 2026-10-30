"""Servidor que imita o protocolo da Replicate, para testar sem chamar o serviço real.

A razão de existir: a API externa de simulação capilar não pode ser chamada nos testes:
não há credencial, custa dinheiro por execução e o domínio está bloqueado no ambiente.
Mas o cliente que fala com ela (`ProvedorReplicate`) é código de produção e precisa ser
exercitado de verdade, inclusive nos caminhos de erro, que são a maior parte dele.

A solução é inverter o alvo: este módulo levanta um servidor HTTP local que responde como
a Replicate responderia, e a configuração da aplicação (`AI_BASE_URL`) passa a apontar
para ele. O cliente exercitado é o mesmo que roda em produção, sem substituição, sem
monkeypatch do seu comportamento. O que muda é só o endereço.

**Os schemas abaixo são uma hipótese**, montada a partir da descrição pública dos modelos
(o domínio da Replicate estava bloqueado no ambiente de desenvolvimento). Eles servem para
exercitar as regras do sistema; o que vale na geração real é o schema que a Replicate
publica, lido ao vivo, e conferido por `python -m app.diagnostico_ia`.

Cenários (variável `cenario`):

    sucesso                 predição conclui e a imagem é entregue
    erro_4xx                401 na criação da predição: credencial recusada
    sem_credito             402: conta sem saldo
    erro_5xx                500: provedor indisponível
    limite                  429: teto de requisições do provedor
    timeout                 a criação demora além do tempo limite
    lento                   demora, mas dentro do tempo limite
    malformada              JSON que não segue o contrato
    vazia                   corpo sem conteúdo
    predicao_falhou         a predição é aceita e depois falha no provedor
    bloqueio_de_seguranca   a predição falha no filtro de segurança do provedor
    imagem_invalida         a URL de saída devolve HTML em vez de imagem
    sem_saida               a predição conclui sem `output`
    processando             a predição fica em andamento por algumas consultas
    nunca_termina           a predição nunca sai de "processing" (e pode ser cancelada)
    consulta_instavel       a primeira consulta do estado responde 503; as seguintes, normal
    saida_instavel          o primeiro download do resultado responde 502; o seguinte entrega
    consulta_fora_do_ar     toda consulta do estado responde 503
    nao_oficial             o modelo não aceita a rota de modelos oficiais (404)
    entrada_recusada        422 na criação: o provedor recusa os parâmetros
    esquema_401             a consulta do schema é recusada por credencial
    modelo_inexistente      a consulta do schema responde 404
    opcoes_diferentes       o schema do principal tem outras opções de corte e cor
    principal_texto_livre   o schema do principal aceita texto livre em haircut/hair_color
    principal_sem_haircut   o schema do principal não tem o campo haircut
    sem_schema              o modelo não publica schema de entrada
"""

from __future__ import annotations

import asyncio
import io
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from PIL import Image

#: Cenário em vigor. Trocado pelo teste antes de cada chamada.
cenario = "sucesso"

#: Predições e arquivos recebidos, para o teste inspecionar o que saiu do sistema.
chamadas: list[dict[str, Any]] = []
#: Consultas de schema (`GET /models/...`): não geram cobrança, ficam à parte.
consultas_de_esquema: list[str] = []
#: Arquivos apagados (`DELETE /files/{id}`) e predições canceladas.
apagados: list[str] = []
cancelamentos: list[str] = []

_consultas_por_predicao: dict[str, int] = {}
#: Downloads do resultado já pedidos (cenário `saida_instavel`).
downloads: list[str] = []

#: Opções supostas do change-haircut (ver o aviso no topo do módulo).
CORTES = [
    "No change", "Random", "Straight", "Wavy", "Curly", "Bob", "Pixie Cut", "Layered",
    "Messy Bun", "High Ponytail", "Low Ponytail", "Braided Ponytail", "French Braid",
    "Undercut", "Mohawk", "Crew Cut", "Faux Hawk", "Slicked Back", "Side-Parted",
    "Center-Parted", "Blunt Bangs", "Side-Swept Bangs", "Shag", "Lob", "Angled Bob",
    "Choppy Layers", "Razor Cut", "Perm", "Soft Waves", "Tousled", "Feathered",
]
CORES = [
    "No change", "Random", "Blonde", "Brunette", "Black", "Dark Brown", "Medium Brown",
    "Light Brown", "Auburn", "Copper", "Red", "Strawberry Blonde", "Platinum Blonde",
    "Silver", "White", "Blue", "Purple", "Pink", "Green", "Blue-Black", "Golden Blonde",
    "Honey Blonde", "Caramel", "Chestnut", "Mahogany", "Burgundy", "Jet Black",
    "Ash Brown", "Ash Blonde", "Titanium", "Rose Gold",
]
PROPORCOES = ["match_input_image", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]


def reiniciar(novo_cenario: str = "sucesso") -> None:
    global cenario
    cenario = novo_cenario
    chamadas.clear()
    consultas_de_esquema.clear()
    apagados.clear()
    cancelamentos.clear()
    _consultas_por_predicao.clear()
    downloads.clear()


def _imagem_gerada() -> bytes:
    """Uma imagem de verdade, para o caminho de sucesso ser realmente percorrido."""
    buffer = io.BytesIO()
    Image.new("RGB", (720, 960), (120, 90, 70)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _opcoes(nome: str, valores: list[str]) -> dict[str, Any]:
    return {"type": "string", "title": nome, "enum": valores, "description": "An enumeration."}


def _schema(propriedades: dict[str, Any], obrigatorios: list[str], componentes: dict[str, Any]) -> dict:
    return {
        "components": {
            "schemas": {
                "Input": {"type": "object", "properties": propriedades, "required": obrigatorios},
                **componentes,
            }
        }
    }


def _ref(nome: str, padrao: str | None = None) -> dict[str, Any]:
    no: dict[str, Any] = {"allOf": [{"$ref": f"#/components/schemas/{nome}"}]}
    if padrao is not None:
        no["default"] = padrao
    return no


def _schema_do_modelo(modelo: str) -> dict[str, Any] | None:
    comuns = {
        "aspect_ratio": _ref("aspect_ratio", "match_input_image"),
        "output_format": _ref("output_format", "png"),
        "seed": {"type": "integer"},
        "safety_tolerance": {"type": "integer", "minimum": 0, "maximum": 2},
    }
    componentes_comuns = {
        "aspect_ratio": _opcoes("aspect_ratio", PROPORCOES),
        "output_format": _opcoes("output_format", ["jpg", "png"]),
    }
    if modelo.endswith("change-haircut"):
        cortes = CORTES
        cores = CORES
        if cenario == "opcoes_diferentes":
            cortes = ["No change", "Random", "Short", "Long"]
            cores = ["No change", "Random", "Dark", "Light"]
        propriedades = {
            "input_image": {"type": "string", "format": "uri"},
            "haircut": _ref("haircut", "No change"),
            "hair_color": _ref("hair_color", "No change"),
            "gender": _ref("gender", "none"),
            **comuns,
        }
        componentes = {
            "haircut": _opcoes("haircut", cortes),
            "hair_color": _opcoes("hair_color", cores),
            "gender": _opcoes("gender", ["none", "male", "female"]),
            **componentes_comuns,
        }
        if cenario == "principal_texto_livre":
            propriedades["haircut"] = {"type": "string", "default": "No change"}
            propriedades["hair_color"] = {"type": "string", "default": "No change"}
        if cenario == "principal_sem_haircut":
            del propriedades["haircut"]
        return _schema(propriedades, ["input_image"], componentes)
    if modelo.endswith("flux-kontext-pro"):
        return _schema(
            {
                "prompt": {"type": "string"},
                "input_image": {"type": "string", "format": "uri"},
                "prompt_upsampling": {"type": "boolean", "default": False},
                **comuns,
            },
            ["prompt"],
            componentes_comuns,
        )
    return None


app = FastAPI(title="Provedor de mentira")


@app.get("/models/{dono}/{modelo}")
async def modelo(dono: str, modelo: str, request: Request):
    consultas_de_esquema.append(f"{dono}/{modelo}")
    if cenario == "esquema_401":
        return JSONResponse(status_code=401, content={"detail": "Invalid token."})
    if cenario == "modelo_inexistente":
        return JSONResponse(status_code=404, content={"detail": "Not found."})
    schema = None if cenario == "sem_schema" else _schema_do_modelo(f"{dono}/{modelo}")
    return JSONResponse(
        content={
            "owner": dono,
            "name": modelo,
            "latest_version": None
            if schema is None
            else {"id": f"versao-{modelo}", "openapi_schema": schema},
        }
    )


def _resumir_entrada(entrada: dict[str, Any]) -> dict[str, Any]:
    """A foto vai como data URI e é grande: guardar só o começo basta."""
    resumo = dict(entrada)
    for chave, valor in entrada.items():
        if isinstance(valor, str) and valor.startswith("data:"):
            resumo[chave] = f"{valor[:40]}... ({len(valor)} caracteres)"
    return resumo


async def _responder_predicao(request: Request, modelo: str, rota: str, corpo: dict) -> Response:
    entrada = dict(corpo.get("input", {}))
    chamadas.append(
        {
            "rota": rota,
            "modelo": modelo,
            "versao": corpo.get("version"),
            # Só se registra *se* havia credencial, nunca o seu valor.
            "tem_credencial": request.headers.get("authorization", "").startswith("Bearer "),
            "input": _resumir_entrada(entrada),
        }
    )

    if cenario == "erro_4xx":
        return JSONResponse(status_code=401, content={"detail": "Invalid token."})
    if cenario == "sem_credito":
        return JSONResponse(status_code=402, content={"detail": "Insufficient credit."})
    if cenario == "erro_5xx":
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})
    if cenario == "entrada_recusada":
        # O corpo do erro pode ecoar a entrada (inclusive a imagem embutida).
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid input", "input": entrada},
        )
    if cenario == "limite":
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded."},
            headers={"Retry-After": "30"},
        )
    if cenario == "malformada":
        # Sem `status`, sem `urls`, sem `output`: nada do que o contrato promete.
        return JSONResponse(status_code=201, content={"coisa": "inesperada"})
    if cenario == "vazia":
        return Response(status_code=201, content=b"", media_type="application/json")
    if cenario == "timeout":
        # Mais longo que qualquer tempo limite que os testes configuram.
        await asyncio.sleep(30)
        return JSONResponse(status_code=201, content={"status": "succeeded"})
    if cenario == "lento":
        await asyncio.sleep(1.5)

    identificador = uuid.uuid4().hex
    base = f"http://{request.url.netloc}"
    urls = {
        "get": f"{base}/predictions/{identificador}",
        "cancel": f"{base}/predictions/{identificador}/cancel",
    }
    if cenario == "predicao_falhou":
        return JSONResponse(
            status_code=201,
            content={"id": identificador, "status": "failed", "error": "CUDA out of memory"},
        )
    if cenario == "bloqueio_de_seguranca":
        return JSONResponse(
            status_code=201,
            content={"id": identificador, "status": "failed", "error": "NSFW content detected"},
        )
    if cenario in ("processando", "nunca_termina", "consulta_instavel", "consulta_fora_do_ar"):
        _consultas_por_predicao[identificador] = 0
        return JSONResponse(
            status_code=201, content={"id": identificador, "status": "starting", "urls": urls}
        )
    return JSONResponse(
        status_code=201,
        content={
            "id": identificador,
            "status": "succeeded",
            "output": _saida(base),
            "urls": urls,
        },
    )


def _saida(base: str) -> Any:
    if cenario == "sem_saida":
        return None
    return f"{base}/saida/nao-e-imagem.html" if cenario == "imagem_invalida" else f"{base}/saida/imagem.jpg"


@app.post("/models/{dono}/{modelo}/predictions")
async def criar_predicao(dono: str, modelo: str, request: Request):
    if cenario == "nao_oficial":
        chamadas.append({"rota": f"/models/{dono}/{modelo}/predictions", "recusada": 404})
        return JSONResponse(status_code=404, content={"detail": "Not found."})
    return await _responder_predicao(
        request, f"{dono}/{modelo}", f"/models/{dono}/{modelo}/predictions", await request.json()
    )


@app.post("/predictions")
async def criar_predicao_por_versao(request: Request):
    corpo = await request.json()
    versao = str(corpo.get("version", ""))
    modelo = versao.removeprefix("versao-")
    return await _responder_predicao(request, modelo, "/predictions", corpo)


@app.get("/predictions/{identificador}")
async def consultar(identificador: str, request: Request):
    """Consulta do estado, usada quando a criação não vem pronta."""
    chamadas.append({"rota": f"/predictions/{identificador}"})
    base = f"http://{request.url.netloc}"
    vezes = _consultas_por_predicao.get(identificador, 99) + 1
    _consultas_por_predicao[identificador] = vezes
    if cenario == "consulta_fora_do_ar" or (cenario == "consulta_instavel" and vezes == 1):
        return JSONResponse(status_code=503, content={"detail": "Service unavailable."})
    if cenario == "nunca_termina" or (cenario == "processando" and vezes < 3):
        return JSONResponse(content={"id": identificador, "status": "processing"})
    return JSONResponse(
        content={"id": identificador, "status": "succeeded", "output": f"{base}/saida/imagem.jpg"}
    )


@app.post("/predictions/{identificador}/cancel")
async def cancelar(identificador: str):
    cancelamentos.append(identificador)
    return JSONResponse(content={"id": identificador, "status": "canceled"})


@app.post("/files")
async def enviar_arquivo(request: Request):
    formulario = await request.form()
    arquivo = formulario.get("content")
    conteudo = await arquivo.read() if arquivo is not None else b""
    identificador = f"arquivo-{uuid.uuid4().hex[:8]}"
    chamadas.append(
        {
            "rota": "/files",
            "bytes": len(conteudo),
            "tipo": getattr(arquivo, "content_type", None),
            "tem_credencial": request.headers.get("authorization", "").startswith("Bearer "),
        }
    )
    return JSONResponse(
        status_code=201,
        content={
            "id": identificador,
            "urls": {"get": f"http://{request.url.netloc}/files/{identificador}"},
        },
    )


@app.delete("/files/{identificador}")
async def apagar_arquivo(identificador: str):
    apagados.append(identificador)
    return Response(status_code=204)


@app.get("/saida/imagem.jpg")
async def imagem():
    downloads.append("imagem.jpg")
    if cenario == "saida_instavel" and len(downloads) == 1:
        return Response(status_code=502, content=b"Bad Gateway")
    return Response(content=_imagem_gerada(), media_type="image/jpeg")


@app.get("/saida/nao-e-imagem.html")
async def nao_e_imagem():
    """O provedor responde 200, com tipo de imagem, mas o conteúdo é uma página de erro.

    É o caso mais traiçoeiro: o código que confia no status e no cabeçalho segue adiante
    e só descobre o problema ao tentar decodificar.
    """
    return Response(
        content=b"<html><body>502 Bad Gateway</body></html>",
        media_type="image/jpeg",
    )
