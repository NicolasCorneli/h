"""Procura travessão (—) e meia-risca (–) em todo texto que o usuário pode ver.

Varre as telas e componentes do aplicativo, o `app.json` e as strings do servidor
(mensagens de erro, textos de demonstração). Comentários e docstrings ficam de fora:
não aparecem para ninguém. Os textos dos termos publicados também ficam de fora, porque
são versões imutáveis guardadas pelas migrations (ver docs/historico/RELATORIO_FINAL_IMPLEMENTACAO.md).

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
print("\n".join(achados))
print(f"\n{len(achados)} ocorrência(s)", file=sys.stderr)
sys.exit(1 if achados else 0)
