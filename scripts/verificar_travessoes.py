"""Procura travessão (—) e meia-risca (–) em todo texto que o usuário pode ver.

Varre as telas e componentes do aplicativo, o `app.json`, as strings do servidor
(mensagens de erro, textos de demonstração) e o termo vigente de cada tipo (cliente e
profissional), que é a versão mais nova publicada pelas migrations. Comentários e
docstrings ficam de fora: não aparecem para ninguém. As versões anteriores dos termos
também ficam de fora, porque são documentos imutáveis, o texto que cada cliente aceitou
(ver docs/historico/RELATORIO_FINAL_IMPLEMENTACAO.md). Até a 1.2 o termo vigente não era
conferido, e os travessões dela chegaram aos testes com usuários; a 1.2.1 os removeu.

Uso: python scripts/verificar_travessoes.py        (a partir da raiz do repositório)
Sai com código 1 se encontrar alguma ocorrência.
"""
import pathlib, re, sys, io, tokenize

raiz = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1])
achados = []
for arq in list(raiz.glob("espelho/app/**/*.tsx")) + list(raiz.glob("espelho/src/**/*.ts*")) + [raiz / "espelho/app.json"]:
    texto = arq.read_text(encoding="utf-8")
    # remove comentários de bloco e de linha (JS/TS/JSX)
    sem = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)
    sem = re.sub(r"\{/\*.*?\*/\}", lambda m: "\n" * m.group(0).count("\n"), sem, flags=re.S)
    for n, linha in enumerate(sem.split("\n"), 1):
        codigo = re.sub(r"(^|[^:])//.*$", r"\1", linha)
        if "—" in codigo or "–" in codigo:
            achados.append(f"{arq.relative_to(raiz)}:{n}: {codigo.strip()[:150]}")
for arq in raiz.glob("backend/app/**/*.py"):
    fonte = arq.read_text(encoding="utf-8")
    for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
        if tok.type == tokenize.STRING and ("—" in tok.string or "–" in tok.string):
            s = tok.string.lstrip("rbfuRBFU")
            if s.startswith(('"""', "'''")):
                continue  # docstrings não aparecem para o usuário
            achados.append(f"{arq.relative_to(raiz)}:{tok.start[0]}: {tok.string[:150]}")
# Termos: só a versão vigente de cada tipo (a mais nova publicada pelas migrations). As
# anteriores são documentos históricos, imutáveis: o texto que cada cliente leu e aceitou.
import ast

def _versao(v):
    return tuple(int(p) for p in v.split("."))

vigentes = {}
for arq in raiz.glob("backend/migrations/versions/*.py"):
    arvore = ast.parse(arq.read_text(encoding="utf-8"))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(getattr(a, "id", None) == "TERMOS" for a in no.targets):
            for termo in ast.literal_eval(no.value):
                tipo, versao = termo["tipo"], termo["versao"]
                if tipo not in vigentes or _versao(versao) > _versao(vigentes[tipo][0]):
                    vigentes[tipo] = (versao, arq, termo)
for tipo, (versao, arq, termo) in sorted(vigentes.items()):
    textos = [termo["titulo"], termo["resumo"]] + [s[c] for s in termo["secoes"] for c in ("titulo", "texto")]
    for texto in textos:
        if "—" in texto or "–" in texto:
            achados.append(f"{arq.relative_to(raiz)}: termo {tipo} {versao}: {texto[:150]}")

print("\n".join(achados))
print(f"\n{len(achados)} ocorrência(s)", file=sys.stderr)
sys.exit(1 if achados else 0)
