"""Compara a qualidade das simulações entre estratégias, com fotos reais e a mesma entrada.

Uso (na pasta `backend`, com o `.env` que já tem a `AI_API_KEY`):

    # Ensaio: mostra o que seria gerado e quanto custaria. Nenhuma chamada é feita.
    python scripts/comparar_simulacoes.py --fotos ../fotos-teste --pedidos scripts/pedidos_cacheados.json \\
        --estrategias nano-original,nano,nano-curvatura

    # Para valer: repita com --confirmar-custo.

Estratégias (`--estrategias`, separadas por vírgula). Cada uma muda uma coisa só em relação
à anterior, para que a diferença entre duas colunas seja efeito daquela mudança:

- `atual`: o caminho especializado (change-haircut e flux-kontext-pro);
- `nano-original`: Nano Banana com a primeira instrução detalhada (2026-11-05);
- `nano`: Nano Banana com a instrução da produção, por prioridades e com a preservação do
  cabelo natural, sem curvatura informada;
- `nano-curvatura`: a anterior com a curvatura informada da foto (precisa do sufixo de
  curvatura no nome do arquivo);
- `nano-textura`: `nano` com uma segunda imagem, um close da textura natural (precisa do
  arquivo `.textura`);
- `nano-referencia`: `nano` com a foto do corte desejado como referência (precisa de
  `referencia_corte` no pedido);
- `nano-etapas`: `nano` em duas chamadas, primeiro o corte e depois a cor sobre o
  resultado (só em pedidos que mudam os dois; custa o dobro).

Estratégia que não se aplica a uma foto ou a um pedido (sem curvatura, sem textura, sem
referência, sem os dois pedidos) fica de fora, e o ensaio diz quantas ficaram.

Fotos (`--fotos`): só de adultos que autorizaram o uso. Cada foto passa pela validação da
produção (`validar_e_normalizar`: tamanho, luz, rosto, EXIF removido); a recusada fica de
fora, com o motivo. Convenções de nome:

- `maria.3C.jpg`: a curvatura natural de "maria" é 3C (aceita as categorias "liso",
  "ondulado", "cacheado", "crespo" ou um tipo de 1A a 4C);
- `maria.textura.jpg`: close da textura natural de "maria" (não é uma foto a simular).

Pedidos (`--pedidos`): lista JSON com `id`, `descricao`, `corte`, `cor`, `manter_corte`,
`manter_cor`, `genero` e, opcional, `referencia_corte` (caminho de uma foto do corte,
relativo ao arquivo de pedidos). Valem as regras da tela (`pedido.interpretar`).

A geração é a do `ProvedorReplicate`, com a montagem de parâmetros e a instrução da
produção: o que este script mostra é o que o aplicativo geraria.

Saída (em `--saida`, padrão `resultados/comparacao-AAAAMMDD-HHMM`):

- `originais/` e `simulacoes/`: as imagens;
- `resultado.csv`: foto, pedido, estratégia, curvatura, modelo, chamadas, tempo, sucesso ou
  código de erro, e a instrução enviada;
- `comparacao.html`: o original e as simulações lado a lado, com notas de 1 a 5 para os
  critérios de `CRITERIOS`. As notas ficam no navegador e podem ser exportadas em CSV.

Preços em `PRECOS` (página de cada modelo na Replicate, consultada em 2026-11-05; ver
docs/NANO_BANANA.md). São estimativas: o valor cobrado é o da fatura da Replicate.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import sys
import time
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.core.config import Configuracao as ConfigServidor  # noqa: E402
from app.core.erros import FotoRecusada, ValidacaoFalhou  # noqa: E402
from app.services.ai.base import EntradaSimulacao, FalhaDoProvedor  # noqa: E402
from app.services.ai.pedido import PedidoCapilar, interpretar, validar_curvatura  # noqa: E402
from app.services.ai.planos import Configuracao, planejar  # noqa: E402
from app.services.validacao_foto import FotoValidada, validar_e_normalizar  # noqa: E402

NANO = "google/nano-banana-2.1"
#: O caminho atual de produção, com os modelos padrão da configuração.
MODELO_PRINCIPAL_ATUAL = ConfigServidor.model_fields["ai_modelo"].default
MODELO_TEXTO_ATUAL = ConfigServidor.model_fields["ai_modelo_texto"].default

#: Dólares por imagem gerada (preço por "output image" publicado na página do modelo).
PRECOS = {
    NANO: {"1K": 0.0336, "2K": 0.0504, "4K": 0.1134},
    MODELO_PRINCIPAL_ATUAL: 0.04,
    MODELO_TEXTO_ATUAL: 0.04,
}

ESTRATEGIAS = (
    "atual",
    "nano-original",
    "nano",
    "nano-curvatura",
    "nano-textura",
    "nano-referencia",
    "nano-etapas",
)

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}
#: Trava contra um laço caro por engano (pasta errada, arquivo de pedidos enorme).
MAXIMO_PADRAO = 60


@dataclass(frozen=True)
class Pedido:
    id: str
    descricao: str
    pedido: PedidoCapilar
    #: Foto do corte desejado (JPEG sem EXIF), para `nano-referencia`.
    referencia_corte: bytes | None = None


@dataclass(frozen=True)
class Foto:
    nome: str
    validada: FotoValidada
    #: Curvatura natural informada no nome do arquivo, para `nano-curvatura`.
    curvatura: str | None = None
    #: Close da textura natural (JPEG sem EXIF), para `nano-textura`.
    textura: bytes | None = None


@dataclass(frozen=True)
class Etapa:
    """Uma chamada ao provedor: o pedido que vai, e sobre qual imagem."""

    pedido: PedidoCapilar
    instrucao: str
    referencias: tuple[bytes, ...] = ()


@dataclass(frozen=True)
class Tarefa:
    foto: Foto
    pedido: Pedido
    caminho: str
    configuracao: Configuracao
    modelo: str
    instrucao: str
    custo: float
    #: Uma etapa, ou duas em `nano-etapas` (a segunda parte da imagem gerada na primeira).
    etapas: tuple[Etapa, ...] = ()


def configuracoes(resolucao: str, idioma: str) -> dict[str, Configuracao]:
    nano = Configuracao(
        modelo_principal=MODELO_PRINCIPAL_ATUAL,
        modelo_texto=NANO,
        estrategia=idioma,  # type: ignore[arg-type]
        caminho="instrucao",
        resolucao=resolucao,
    )
    return {
        "atual": Configuracao(
            modelo_principal=MODELO_PRINCIPAL_ATUAL,
            modelo_texto=MODELO_TEXTO_ATUAL,
            estrategia=idioma,  # type: ignore[arg-type]
            caminho="especializado",
        ),
        "nano-original": replace(nano, variante_instrucao="original"),
        **{nome: nano for nome in ESTRATEGIAS if nome.startswith("nano") and nome != "nano-original"},
    }


def preco(modelo: str, resolucao: str) -> float:
    valor = PRECOS.get(modelo)
    if isinstance(valor, dict):
        return valor[resolucao]
    if valor is None:
        raise SystemExit(f"Sem preço conhecido para {modelo}: atualize PRECOS antes de gastar.")
    return valor


def _jpeg_sem_metadados(conteudo: bytes) -> bytes:
    """Referências não passam pela validação de rosto (um close de cabelo não tem rosto),
    mas saem como a foto: JPEG regravado, sem EXIF."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(conteudo)) as imagem:
        copia = ImageOps.exif_transpose(imagem).convert("RGB")
    saida = io.BytesIO()
    copia.save(saida, format="JPEG", quality=90)
    return saida.getvalue()


def ler_pedidos(arquivo: Path) -> list[Pedido]:
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    pedidos = []
    for indice, item in enumerate(dados, start=1):
        identificador = str(item.get("id") or f"pedido-{indice}")
        try:
            pedido = interpretar(
                item.get("corte"),
                item.get("cor"),
                manter_corte=bool(item.get("manter_corte")),
                manter_cor=bool(item.get("manter_cor")),
                genero=item.get("genero"),
            )
        except ValidacaoFalhou as erro:
            raise SystemExit(f"Pedido {identificador} inválido: {erro}") from erro
        referencia = None
        if item.get("referencia_corte"):
            caminho = (arquivo.parent / item["referencia_corte"]).resolve()
            if not caminho.exists():
                raise SystemExit(f"Pedido {identificador}: referência não encontrada em {caminho}")
            referencia = _jpeg_sem_metadados(caminho.read_bytes())
        pedidos.append(Pedido(identificador, str(item.get("descricao") or ""), pedido, referencia))
    return pedidos


def ler_fotos(pasta: Path) -> list[Foto]:
    texturas = {
        arquivo.name.split(".")[0]: _jpeg_sem_metadados(arquivo.read_bytes())
        for arquivo in pasta.iterdir()
        if arquivo.suffix.lower() in EXTENSOES and ".textura." in arquivo.name.lower()
    }
    fotos = []
    for arquivo in sorted(pasta.iterdir()):
        if arquivo.suffix.lower() not in EXTENSOES or ".textura." in arquivo.name.lower():
            continue
        partes = arquivo.name.split(".")
        nome = partes[0]
        curvatura = None
        if len(partes) > 2:
            try:
                curvatura = validar_curvatura(partes[1])
            except ValidacaoFalhou:
                print(f"  sufixo de curvatura não reconhecido em {arquivo.name}: ignorado")
        try:
            validada = validar_e_normalizar(arquivo.read_bytes())
        except FotoRecusada as recusa:
            motivos = "; ".join(p.get("titulo", "") for p in (recusa.detalhes or []))
            print(f"  foto recusada pela validação, fica de fora: {arquivo.name} ({motivos or recusa})")
            continue
        fotos.append(Foto(nome, validada, curvatura, texturas.get(nome)))
    return fotos


def _etapas(foto: Foto, pedido: Pedido, estrategia: str, configuracao: Configuracao) -> tuple[Etapa, ...] | None:
    """O que cada estratégia manda ao provedor; None quando ela não se aplica."""
    base = replace(pedido.pedido, curvatura=None, referencias=())

    def etapa(p: PedidoCapilar, referencias: tuple[bytes, ...] = ()) -> Etapa:
        return Etapa(p, planejar(p, configuracao).instrucao, referencias)

    if estrategia in ("atual", "nano-original", "nano"):
        return (etapa(base),)
    if estrategia == "nano-curvatura":
        return (etapa(replace(base, curvatura=foto.curvatura)),) if foto.curvatura else None
    if estrategia == "nano-textura":
        if foto.textura is None:
            return None
        return (etapa(replace(base, referencias=("textura",)), (foto.textura,)),)
    if estrategia == "nano-referencia":
        if pedido.referencia_corte is None or base.corte is None:
            return None
        return (etapa(replace(base, referencias=("corte",)), (pedido.referencia_corte,)),)
    if estrategia == "nano-etapas":
        if base.corte is None or base.cor is None:
            return None
        return (etapa(replace(base, cor=None)), etapa(replace(base, corte=None)))
    raise ValueError(estrategia)


def planejar_tarefas(
    fotos: list[Foto], pedidos: list[Pedido], caminhos: list[str], resolucao: str, idioma: str
) -> list[Tarefa]:
    """O que será gerado, sem consultar o provedor (o schema ao vivo confere na geração)."""
    disponiveis = configuracoes(resolucao, idioma)
    tarefas = []
    puladas = 0
    for foto in fotos:
        for pedido in pedidos:
            for caminho in caminhos:
                configuracao = disponiveis[caminho]
                etapas = _etapas(foto, pedido, caminho, configuracao)
                if etapas is None:
                    puladas += 1
                    continue
                modelo = planejar(etapas[0].pedido, configuracao).modelo
                tarefas.append(
                    Tarefa(
                        foto,
                        pedido,
                        caminho,
                        configuracao,
                        modelo,
                        "\n\n".join(e.instrucao for e in etapas),
                        sum(preco(planejar(e.pedido, configuracao).modelo, resolucao) for e in etapas),
                        etapas,
                    )
                )
    if puladas:
        print(f"  {puladas} combinação(ões) de foto, pedido e estratégia não se aplicam e ficam de fora.")
    return tarefas


def resumir(tarefas: list[Tarefa]) -> None:
    chamadas = sum(len(t.etapas) for t in tarefas)
    total = sum(t.custo for t in tarefas)
    print(f"\n{chamadas} chamada(s) ao provedor, custo estimado: US$ {total:.2f}")
    por_estrategia: dict[str, list[Tarefa]] = {}
    for tarefa in tarefas:
        por_estrategia.setdefault(tarefa.caminho, []).append(tarefa)
    for estrategia, lista in por_estrategia.items():
        custo = sum(t.custo for t in lista)
        print(f"  {estrategia} ({lista[0].modelo}): {sum(len(t.etapas) for t in lista)} chamada(s), US$ {custo:.2f}")
    print("\nInstruções (uma por pedido e estratégia):")
    vistos = set()
    for tarefa in tarefas:
        chave = (tarefa.pedido.id, tarefa.caminho, tarefa.foto.curvatura)
        if chave in vistos:
            continue
        vistos.add(chave)
        print(f"\n  [{tarefa.pedido.id} · {tarefa.caminho} · {tarefa.modelo}]")
        print(f"  {tarefa.instrucao}")


def gerar(tarefas: list[Tarefa], saida: Path) -> list[dict]:
    from app.services.ai.replicate import ProvedorReplicate

    (saida / "originais").mkdir(parents=True, exist_ok=True)
    (saida / "simulacoes").mkdir(parents=True, exist_ok=True)
    provedores: dict[str, ProvedorReplicate] = {}
    linhas = []
    for numero, tarefa in enumerate(tarefas, start=1):
        original = saida / "originais" / f"{tarefa.foto.nome}.jpg"
        if not original.exists():
            original.write_bytes(tarefa.foto.validada.conteudo)
        provedor = provedores.setdefault(tarefa.caminho, ProvedorReplicate(tarefa.configuracao))
        print(f"[{numero}/{len(tarefas)}] {tarefa.foto.nome} · {tarefa.pedido.id} · {tarefa.caminho} ...", end=" ", flush=True)
        inicio = time.monotonic()
        linha = {
            "foto": tarefa.foto.nome,
            "pedido": tarefa.pedido.id,
            "descricao_pedido": tarefa.pedido.descricao,
            "corte": tarefa.pedido.pedido.rotulo_corte,
            "cor": tarefa.pedido.pedido.rotulo_cor,
            "genero": tarefa.pedido.pedido.genero,
            "curvatura": tarefa.foto.curvatura or "",
            "caminho": tarefa.caminho,
            "modelo": tarefa.modelo,
            "chamadas": len(tarefa.etapas),
            "tempo_ms": "",
            "sucesso": "nao",
            "codigo_erro": "",
            "arquivo": "",
            "instrucao": tarefa.instrucao,
        }
        imagem = tarefa.foto.validada.conteudo
        tempo_ms = 0
        instrucoes = []
        try:
            for etapa in tarefa.etapas:
                # Em `nano-etapas`, a segunda etapa parte da imagem gerada na primeira.
                resultado = provedor.gerar(
                    EntradaSimulacao(imagem=imagem, mime="image/jpeg", pedido=etapa.pedido, referencias=etapa.referencias)
                )
                imagem = _como_jpeg(resultado.imagem)
                tempo_ms += resultado.tempo_ms
                instrucoes.append(resultado.instrucao)
        except FalhaDoProvedor as erro:
            linha["tempo_ms"] = int((time.monotonic() - inicio) * 1000)
            linha["codigo_erro"] = erro.codigo
            print(f"falhou ({erro.codigo})")
        else:
            nome = f"{tarefa.foto.nome}__{tarefa.pedido.id}__{tarefa.caminho}.jpg"
            (saida / "simulacoes" / nome).write_bytes(imagem)
            linha.update(
                tempo_ms=tempo_ms,
                sucesso="sim",
                arquivo=f"simulacoes/{nome}",
                modelo=resultado.modelo,
                instrucao="\n\n".join(instrucoes),
            )
            print(f"ok em {tempo_ms / 1000:.1f} s")
        linhas.append(linha)
    return linhas

def _como_jpeg(conteudo: bytes) -> bytes:
    """A saída pode vir em PNG: grava sempre JPEG, para a página abrir tudo igual."""
    from PIL import Image

    with Image.open(io.BytesIO(conteudo)) as imagem:
        if imagem.format == "JPEG":
            return conteudo
        saida = io.BytesIO()
        imagem.convert("RGB").save(saida, format="JPEG", quality=92)
        return saida.getvalue()


CAMPOS_CSV = [
    "foto", "pedido", "descricao_pedido", "corte", "cor", "genero", "curvatura", "caminho",
    "modelo", "chamadas", "tempo_ms", "sucesso", "codigo_erro", "arquivo", "instrucao",
]


def gravar_csv(linhas: list[dict], arquivo: Path) -> None:
    with arquivo.open("w", newline="", encoding="utf-8-sig") as destino:
        escritor = csv.DictWriter(destino, fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        escritor.writerows(linhas)


#: Os critérios da avaliação (docs/NANO_BANANA.md, seção 10). Curvatura, textura, volume e
#: comprimento vêm do relato dos testes ("abriu meus cachos", "aumentou o comprimento").
CRITERIOS = (
    ("identidade", "Identidade"),
    ("curvatura", "Curvatura"),
    ("textura", "Textura"),
    ("comprimento", "Comprimento"),
    ("volume", "Volume"),
    ("corte", "Corte"),
    ("cor", "Cor"),
    ("naturalidade", "Naturalidade"),
)


def gravar_html(linhas: list[dict], arquivo: Path, titulo: str) -> None:
    """Página estática para avaliar: original e simulações lado a lado, com notas de 1 a 5."""
    e = html.escape
    grupos: dict[tuple[str, str], list[dict]] = {}
    for linha in linhas:
        grupos.setdefault((linha["foto"], linha["pedido"]), []).append(linha)

    blocos = []
    for (foto, pedido), resultados in grupos.items():
        primeiro = resultados[0]
        cartoes = [
            f'<figure class="cartao"><img src="originais/{e(foto)}.jpg" alt="Original {e(foto)}" loading="lazy">'
            f"<figcaption><strong>Original</strong></figcaption></figure>"
        ]
        for r in resultados:
            chave = f"{foto}|{pedido}|{r['caminho']}"
            if r["sucesso"] == "sim":
                imagem = f'<img src="{e(r["arquivo"])}" alt="{e(r["caminho"])}" loading="lazy">'
            else:
                imagem = f'<div class="falha">Falhou: {e(r["codigo_erro"])}</div>'
            notas = "".join(
                f'<label>{e(rotulo)} <select data-chave="{e(chave)}" data-criterio="{criterio}">'
                + '<option value="">–</option>'
                + "".join(f'<option value="{n}">{n}</option>' for n in range(1, 6))
                + "</select></label>"
                for criterio, rotulo in CRITERIOS
            )
            cartoes.append(
                f'<figure class="cartao">{imagem}<figcaption><strong>{e(r["caminho"])}</strong> · '
                f'{e(r["modelo"])} · {e(str(r["tempo_ms"]))} ms<div class="notas">{notas}'
                f'<textarea data-chave="{e(chave)}" data-criterio="observacao" rows="2" '
                f'placeholder="Observação"></textarea></div>'
                f'<details><summary>Instrução enviada</summary><p>{e(r["instrucao"])}</p></details>'
                f"</figcaption></figure>"
            )
        blocos.append(
            f'<section><h2>{e(foto)} · {e(pedido)}</h2><p class="pedido">Corte: {e(primeiro["corte"])} · '
            f'Cor: {e(primeiro["cor"])} · Gênero: {e(primeiro["genero"])}'
            f'{" · Curvatura informada: " + e(primeiro["curvatura"]) if primeiro["curvatura"] else ""}'
            f'{" · " + e(primeiro["descricao_pedido"]) if primeiro["descricao_pedido"] else ""}</p>'
            f'<div class="grade">{"".join(cartoes)}</div></section>'
        )

    arquivo.write_text(
        f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<style>
:root {{ --fundo:#F8F6F3; --tinta:#1F1A22; --apoio:#574E5C; --borda:#E3DDE1; --acao:#6B2D5C; }}
body {{ margin:0; background:var(--fundo); color:var(--tinta); font:15px/1.5 system-ui, sans-serif; padding:24px max(16px, 3vw); }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:0; }}
.topo {{ display:flex; flex-wrap:wrap; gap:12px; align-items:end; justify-content:space-between; margin-bottom:24px; }}
section {{ border-top:1px solid var(--borda); padding:20px 0; }}
.pedido {{ color:var(--apoio); margin:4px 0 12px; }}
.grade {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:16px; }}
.cartao {{ margin:0; background:#fff; border:1px solid var(--borda); border-radius:12px; overflow:hidden; }}
.cartao img {{ width:100%; display:block; aspect-ratio:3/4; object-fit:contain; background:#EEE9EC; }}
.falha {{ aspect-ratio:3/4; display:grid; place-items:center; background:#FCEBE8; color:#A12B21; font-weight:600; }}
figcaption {{ padding:10px 12px; font-size:13px; color:var(--apoio); }}
figcaption strong {{ color:var(--tinta); }}
.notas {{ display:grid; gap:6px; margin-top:8px; }}
.notas label {{ display:flex; justify-content:space-between; gap:8px; }}
textarea {{ width:100%; box-sizing:border-box; font:inherit; }}
details p {{ font-size:12px; white-space:pre-wrap; }}
button {{ background:var(--acao); color:#fff; border:0; border-radius:8px; padding:10px 16px; font:inherit; font-weight:600; cursor:pointer; }}
</style></head><body>
<div class="topo"><div><h1>{e(titulo)}</h1><p class="pedido">Notas de 1 (ruim) a 5 (ótimo). Elas ficam salvas neste navegador.</p></div>
<button type="button" id="exportar">Exportar notas (CSV)</button></div>
{"".join(blocos)}
<script>
const CHAVE = 'notas:' + {json.dumps(titulo)};
let notas = {{}};
try {{ notas = JSON.parse(localStorage.getItem(CHAVE) || '{{}}'); }} catch (_) {{}}
document.querySelectorAll('[data-chave]').forEach((campo) => {{
  const id = campo.dataset.chave + '|' + campo.dataset.criterio;
  if (notas[id]) campo.value = notas[id];
  campo.addEventListener('input', () => {{
    notas[id] = campo.value;
    try {{ localStorage.setItem(CHAVE, JSON.stringify(notas)); }} catch (_) {{}}
  }});
}});
document.getElementById('exportar').addEventListener('click', () => {{
  const linhas = [['foto', 'pedido', 'caminho', 'criterio', 'valor']];
  Object.entries(notas).forEach(([id, valor]) => {{ if (valor) linhas.push([...id.split('|'), valor]); }});
  const csv = linhas.map((l) => l.map((c) => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob(['\\ufeff' + csv], {{ type: 'text/csv' }}));
  link.download = 'notas.csv';
  link.click();
}});
</script></body></html>
""",
        encoding="utf-8",
    )


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    leitor.add_argument("--fotos", type=Path, required=True, help="pasta com as fotos (adultos que autorizaram)")
    leitor.add_argument("--pedidos", type=Path, required=True, help="arquivo JSON com os pedidos")
    leitor.add_argument("--estrategias", default="nano", help=f"separadas por vírgula: {', '.join(ESTRATEGIAS)}")
    leitor.add_argument("--resolucao", default="1K", choices=["1K", "2K", "4K"], help="resolução do Nano Banana")
    leitor.add_argument("--saida", type=Path, help="pasta de saída")
    leitor.add_argument("--maximo", type=int, default=MAXIMO_PADRAO, help="teto de chamadas desta execução")
    leitor.add_argument("--confirmar-custo", action="store_true", help="faz as chamadas pagas (sem isto, só ensaio)")
    args = leitor.parse_args(argumentos)

    caminhos = [c.strip() for c in args.estrategias.split(",") if c.strip()]
    desconhecidos = sorted(set(caminhos) - set(ESTRATEGIAS))
    if not caminhos or desconhecidos:
        leitor.error(f"--estrategias aceita {', '.join(ESTRATEGIAS)} (recebido: {args.estrategias})")

    from app.core.config import obter_config

    config = obter_config()
    pedidos = ler_pedidos(args.pedidos)
    print(f"Fotos em {args.fotos}:")
    fotos = ler_fotos(args.fotos)
    if not fotos:
        print("Nenhuma foto aprovada pela validação: nada a gerar.")
        return 1
    tarefas = planejar_tarefas(fotos, pedidos, caminhos, args.resolucao, config.ai_instrucao_idioma)
    print(f"{len(fotos)} foto(s) x {len(pedidos)} pedido(s) x {len(caminhos)} caminho(s)")
    resumir(tarefas)

    chamadas = sum(len(t.etapas) for t in tarefas)
    if chamadas > args.maximo:
        print(f"\n{chamadas} chamadas passam do teto (--maximo {args.maximo}). Reduza fotos ou pedidos, ou aumente o teto.")
        return 1
    if not args.confirmar_custo:
        print("\nEnsaio: nenhuma chamada foi feita. Para gerar (e pagar), repita com --confirmar-custo.")
        return 0
    if not config.ai_api_key:
        print("\nAI_API_KEY não configurada no .env: não há como gerar.")
        return 1

    saida = args.saida or RAIZ / "resultados" / f"comparacao-{datetime.now():%Y%m%d-%H%M}"
    print(f"\nGerando em {saida} ...")
    linhas = gerar(tarefas, saida)
    gravar_csv(linhas, saida / "resultado.csv")
    gravar_html(linhas, saida / "comparacao.html", f"Comparação de simulações · {saida.name}")
    falhas = sum(1 for linha in linhas if linha["sucesso"] != "sim")
    print(f"\nPronto: {len(linhas) - falhas} imagem(ns), {falhas} falha(s).")
    print(f"Abra {saida / 'comparacao.html'} no navegador para dar as notas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
