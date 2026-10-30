"""Confere, sem gastar crédito, se os modelos configurados aceitam o que o sistema envia.

Uso (na pasta `backend`, com o `.env` preenchido):

    python -m app.diagnostico_ia

Para cada modelo configurado (`AI_MODELO` e `AI_MODELO_TEXTO`), lê o schema publicado na
Replicate (`GET /models/...`, que não gera cobrança) e confere:

- se o modelo existe e a credencial é aceita;
- se os campos que o sistema envia existem no schema;
- no modelo principal, se cada exemplo do catálogo tem equivalente nas opções publicadas
  de `haircut` e `hair_color` (os que não tiverem vão pelo modelo de descrição livre).

Nenhuma predição é criada, nenhuma imagem é enviada e a chave não é impressa.
Sai com código 1 se encontrar algum problema.
"""

from __future__ import annotations

import sys

import httpx

from app.core.config import obter_config
from app.services.ai.base import FalhaDoProvedor
from app.services.ai.esquema import EsquemaModelo
from app.services.catalogo import CORES, CORTES


def _mostrar_campos(esquema: EsquemaModelo) -> None:
    for nome, campo in esquema.campos.items():
        marca = "obrigatório" if campo.obrigatorio else "opcional"
        if campo.opcoes is not None:
            amostra = ", ".join(campo.opcoes[:8]) + (" …" if len(campo.opcoes) > 8 else "")
            print(f"    - {nome} ({marca}; {len(campo.opcoes)} opções: {amostra})")
        else:
            print(f"    - {nome} ({marca}; {campo.tipo or 'sem tipo'}{', ' + campo.formato if campo.formato else ''})")


def main() -> int:
    config = obter_config()
    if config.ai_provider != "replicate":
        print("AI_PROVIDER não é 'replicate': nada a conferir (o provedor local não usa modelos).")
        return 0

    from app.services.ai.replicate import ProvedorReplicate

    try:
        provedor = ProvedorReplicate()
    except FalhaDoProvedor as erro:
        print(f"ERRO: {erro}")
        return 1

    problemas: list[str] = []
    modelos = {
        "principal (AI_MODELO)": config.ai_modelo,
        "descrição livre (AI_MODELO_TEXTO)": config.ai_modelo_texto,
    }
    esperados = {
        config.ai_modelo: {"input_image", "haircut", "hair_color"},
        config.ai_modelo_texto: {"input_image", "prompt"},
    }

    with httpx.Client(timeout=30.0) as cliente:
        for papel, modelo in modelos.items():
            print(f"\n{papel}: {modelo or '(desligado)'}")
            if not modelo:
                continue
            try:
                esquema = provedor.esquema(cliente, modelo)
            except FalhaDoProvedor as erro:
                problemas.append(f"{modelo}: {erro} ({erro.codigo})")
                print(f"  ERRO: {erro} ({erro.codigo})")
                continue
            except httpx.HTTPError as erro:
                problemas.append(f"{modelo}: sem resposta do provedor ({type(erro).__name__})")
                print(f"  ERRO: sem resposta do provedor ({type(erro).__name__})")
                continue
            if esquema is None:
                problemas.append(f"{modelo}: schema de entrada não publicado")
                print("  AVISO: o modelo não publicou schema de entrada; o envio seguirá sem conferência.")
                continue
            print(f"  versão: {esquema.versao}")
            print("  campos:")
            _mostrar_campos(esquema)
            faltando = sorted(esperados.get(modelo, set()) - set(esquema.campos))
            if faltando:
                problemas.append(f"{modelo}: faltam os campos {faltando}")
                print(f"  PROBLEMA: o sistema envia campos que o schema não tem: {faltando}")

            if modelo == config.ai_modelo:
                for nome_campo, opcoes in (("haircut", CORTES), ("hair_color", CORES)):
                    campo = esquema.campos.get(nome_campo)
                    if campo is None:
                        continue
                    if campo.opcoes is None:
                        print(f"  {nome_campo}: aceita texto livre (as descrições vão direto neste modelo).")
                        continue
                    for opcao in opcoes:
                        if not opcao.opcoes_do_modelo:
                            print(f"  {nome_campo}: '{opcao.rotulo}' sem equivalente (vai pela descrição livre).")
                            continue
                        achado = next(
                            (campo.opcao_equivalente(c) for c in opcao.opcoes_do_modelo if campo.opcao_equivalente(c)),
                            None,
                        )
                        if achado:
                            print(f"  {nome_campo}: '{opcao.rotulo}' -> '{achado}' (ok)")
                        else:
                            print(
                                f"  {nome_campo}: '{opcao.rotulo}' esperava {list(opcao.opcoes_do_modelo)}, "
                                "que não está nas opções publicadas: irá pela descrição livre."
                            )

    print()
    if problemas:
        print("Problemas encontrados:")
        for problema in problemas:
            print(f"  - {problema}")
        return 1
    print("Tudo conferido: os modelos configurados aceitam o que o sistema envia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
