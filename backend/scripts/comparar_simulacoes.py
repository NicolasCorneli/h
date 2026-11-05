"""Compara a qualidade das simulações entre caminhos (Nano Banana e o atual), com fotos reais.

Uso (na pasta `backend`, com o `.env` que já tem a `AI_API_KEY`):

    # Ensaio: mostra o que seria gerado e quanto custaria. Nenhuma chamada é feita.
    python scripts/comparar_simulacoes.py --fotos ../fotos-teste --pedidos scripts/pedidos_exemplo.json

    # Para valer, pelos dois caminhos, lado a lado:
    python scripts/comparar_simulacoes.py --fotos ../fotos-teste --pedidos scripts/pedidos_exemplo.json \\
        --estrategias nano,atual --confirmar-custo

Use só fotos de adultos que autorizaram o uso. Cada foto passa pela mesma validação da
produção (`validar_e_normalizar`: tamanho, luz, rosto, EXIF removido); a que for recusada
fica de fora, com o motivo. Cada pedido passa pelas mesmas regras da tela
(`pedido.interpretar`). A geração é a do `ProvedorReplicate`, com a montagem de parâmetros e
a instrução da produção: o que este script mostra é o que o aplicativo geraria.

Saída (em `--saida`, padrão `resultados/comparacao-AAAAMMDD-HHMM`):

- `originais/` e `simulacoes/`: as imagens;
- `resultado.csv`: foto, pedido, caminho, modelo, tempo, sucesso ou código de erro, e a
  instrução enviada;
- `comparacao.html`: página estática com o original e as simulações lado a lado e notas de
  1 a 5 (naturalidade, fidelidade da cor, preservação do rosto) para preencher. As notas
  ficam no navegador e podem ser exportadas em CSV.

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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.core.config import Configuracao as ConfigServidor  # noqa: E402
from app.core.erros import FotoRecusada, ValidacaoFalhou  # noqa: E402
from app.services.ai.base import EntradaSimulacao, FalhaDoProvedor  # noqa: E402
from app.services.ai.pedido import PedidoCapilar, interpretar  # noqa: E402
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

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}
#: Trava contra um laço caro por engano (pasta errada, arquivo de pedidos enorme).
MAXIMO_PADRAO = 60


@dataclass(frozen=True)
class Pedido:
    id: str
    descricao: str
    pedido: PedidoCapilar


@dataclass(frozen=True)
class Foto:
    nome: str
    validada: FotoValidada


@dataclass(frozen=True)
class Tarefa:
    foto: Foto
    pedido: Pedido
    caminho: str
    configuracao: Configuracao
    modelo: str
    instrucao: str
    custo: float


def configuracoes(resolucao: str, idioma: str) -> dict[str, Configuracao]:
    return {
        "nano": Configuracao(
            modelo_principal=MODELO_PRINCIPAL_ATUAL,
            modelo_texto=NANO,
            estrategia=idioma,  # type: ignore[arg-type]
            caminho="instrucao",
            resolucao=resolucao,
        ),
        "atual": Configuracao(
            modelo_principal=MODELO_PRINCIPAL_ATUAL,
            modelo_texto=MODELO_TEXTO_ATUAL,
            estrategia=idioma,  # type: ignore[arg-type]
            caminho="especializado",
        ),
    }


def preco(modelo: str, resolucao: str) -> float:
    valor = PRECOS.get(modelo)
    if isinstance(valor, dict):
        return valor[resolucao]
    if valor is None:
        raise SystemExit(f"Sem preço conhecido para {modelo}: atualize PRECOS antes de gastar.")
    return valor


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
        pedidos.append(Pedido(identificador, str(item.get("descricao") or ""), pedido))
    return pedidos


def ler_fotos(pasta: Path) -> list[Foto]:
    fotos = []
    for arquivo in sorted(pasta.iterdir()):
        if arquivo.suffix.lower() not in EXTENSOES:
            continue
        try:
            fotos.append(Foto(arquivo.stem, validar_e_normalizar(arquivo.read_bytes())))
        except FotoRecusada as recusa:
            motivos = "; ".join(p.get("titulo", "") for p in (recusa.detalhes or []))
            print(f"  foto recusada pela validação, fica de fora: {arquivo.name} ({motivos or recusa})")
    return fotos


def planejar_tarefas(
    fotos: list[Foto], pedidos: list[Pedido], caminhos: list[str], resolucao: str, idioma: str
) -> list[Tarefa]:
    """O que será gerado, sem consultar o provedor (o schema ao vivo confere na geração)."""
    disponiveis = configuracoes(resolucao, idioma)
    tarefas = []
    for foto in fotos:
        for pedido in pedidos:
            for caminho in caminhos:
                configuracao = disponiveis[caminho]
                plano = planejar(pedido.pedido, configuracao)
                tarefas.append(
                    Tarefa(foto, pedido, caminho, configuracao, plano.modelo, plano.instrucao, preco(plano.modelo, resolucao))
                )
    return tarefas


def resumir(tarefas: list[Tarefa]) -> None:
    total = sum(t.custo for t in tarefas)
    print(f"\n{len(tarefas)} chamada(s) ao provedor, custo estimado: US$ {total:.2f}")
    por_modelo: dict[str, list[Tarefa]] = {}
    for tarefa in tarefas:
        por_modelo.setdefault(tarefa.modelo, []).append(tarefa)
    for modelo, lista in por_modelo.items():
        print(f"  {modelo}: {len(lista)} x US$ {lista[0].custo:.4f}")
    print("\nInstruções (uma por pedido e caminho):")
    vistos = set()
    for tarefa in tarefas:
        chave = (tarefa.pedido.id, tarefa.caminho)
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
            "caminho": tarefa.caminho,
            "modelo": tarefa.modelo,
            "tempo_ms": "",
            "sucesso": "nao",
            "codigo_erro": "",
            "arquivo": "",
            "instrucao": tarefa.instrucao,
        }
        try:
            resultado = provedor.gerar(
                EntradaSimulacao(imagem=tarefa.foto.validada.conteudo, mime=tarefa.foto.validada.mime, pedido=tarefa.pedido.pedido)
            )
        except FalhaDoProvedor as erro:
            linha["tempo_ms"] = int((time.monotonic() - inicio) * 1000)
            linha["codigo_erro"] = erro.codigo
            print(f"falhou ({erro.codigo})")
        else:
            nome = f"{tarefa.foto.nome}__{tarefa.pedido.id}__{tarefa.caminho}.jpg"
            (saida / "simulacoes" / nome).write_bytes(_como_jpeg(resultado.imagem))
            linha.update(
                tempo_ms=resultado.tempo_ms,
                sucesso="sim",
                arquivo=f"simulacoes/{nome}",
                modelo=resultado.modelo,
                instrucao=resultado.instrucao,
            )
            print(f"ok em {resultado.tempo_ms / 1000:.1f} s")
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
    "foto", "pedido", "descricao_pedido", "corte", "cor", "genero", "caminho", "modelo",
    "tempo_ms", "sucesso", "codigo_erro", "arquivo", "instrucao",
]


def gravar_csv(linhas: list[dict], arquivo: Path) -> None:
    with arquivo.open("w", newline="", encoding="utf-8-sig") as destino:
        escritor = csv.DictWriter(destino, fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        escritor.writerows(linhas)


CRITERIOS = (
    ("naturalidade", "Naturalidade"),
    ("cor", "Fidelidade da cor"),
    ("rosto", "Preservação do rosto"),
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
    leitor.add_argument("--estrategias", default="nano", help="caminhos separados por vírgula: nano, atual")
    leitor.add_argument("--resolucao", default="1K", choices=["1K", "2K", "4K"], help="resolução do Nano Banana")
    leitor.add_argument("--saida", type=Path, help="pasta de saída")
    leitor.add_argument("--maximo", type=int, default=MAXIMO_PADRAO, help="teto de chamadas desta execução")
    leitor.add_argument("--confirmar-custo", action="store_true", help="faz as chamadas pagas (sem isto, só ensaio)")
    args = leitor.parse_args(argumentos)

    caminhos = [c.strip() for c in args.estrategias.split(",") if c.strip()]
    desconhecidos = sorted(set(caminhos) - {"nano", "atual"})
    if not caminhos or desconhecidos:
        leitor.error(f"--estrategias aceita nano e atual (recebido: {args.estrategias})")

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

    if len(tarefas) > args.maximo:
        print(f"\n{len(tarefas)} chamadas passam do teto (--maximo {args.maximo}). Reduza fotos ou pedidos, ou aumente o teto.")
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
