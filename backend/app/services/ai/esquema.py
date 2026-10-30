"""Leitura do schema de entrada publicado pela Replicate para cada modelo.

`GET /v1/models/{dono}/{nome}` devolve a versão mais recente com o OpenAPI dela. É dali
que sai a lista de campos aceitos, quais são obrigatórios e, para os campos de opções
fechadas (como `haircut` no `change-haircut`), os valores permitidos.

O servidor confere cada envio contra esse schema **antes** de criar a predição. Assim,
um campo que o modelo não tem, ou um valor fora das opções, é barrado aqui, com um motivo
claro, em vez de virar um 422 genérico do provedor (ou, pior, ser ignorado em silêncio).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Campo:
    nome: str
    tipo: str | None = None
    #: Valores permitidos, quando o campo é de opções fechadas. None: texto livre.
    opcoes: tuple[str, ...] | None = None
    obrigatorio: bool = False
    formato: str | None = None

    def aceita(self, valor: object) -> bool:
        return self.opcoes is None or valor in self.opcoes

    def opcao_equivalente(self, candidato: str) -> str | None:
        """O valor exato da lista que corresponde ao candidato, sem diferenciar caixa."""
        if self.opcoes is None:
            return None
        chave = candidato.strip().lower()
        for opcao in self.opcoes:
            if str(opcao).strip().lower() == chave:
                return str(opcao)
        return None


@dataclass(frozen=True)
class EsquemaModelo:
    modelo: str
    #: Identificador da versão mais recente (necessário para modelos que não são
    #: "oficiais" na Replicate e só aceitam `POST /predictions` com `version`).
    versao: str | None
    campos: dict[str, Campo] = field(default_factory=dict)

    @property
    def obrigatorios(self) -> list[str]:
        return [nome for nome, campo in self.campos.items() if campo.obrigatorio]


def _resolver(no: dict[str, Any], componentes: dict[str, Any]) -> dict[str, Any]:
    """Segue `$ref` e `allOf` (é assim que a Replicate descreve campos de opções)."""
    resolvido = dict(no)
    referencia = resolvido.pop("$ref", None)
    if isinstance(referencia, str) and referencia.startswith("#/components/schemas/"):
        alvo = componentes.get(referencia.rsplit("/", 1)[-1], {})
        resolvido = {**_resolver(alvo, componentes), **resolvido}
    for parte in resolvido.pop("allOf", []) or []:
        if isinstance(parte, dict):
            resolvido = {**_resolver(parte, componentes), **resolvido}
    return resolvido


def ler_esquema(modelo: str, dados: dict[str, Any]) -> EsquemaModelo | None:
    """Extrai os campos de entrada do JSON do modelo. None se não houver schema publicado."""
    versao = dados.get("latest_version") if isinstance(dados, dict) else None
    if not isinstance(versao, dict):
        return None
    openapi = versao.get("openapi_schema") or {}
    componentes = (openapi.get("components") or {}).get("schemas") or {}
    entrada = componentes.get("Input")
    if not isinstance(entrada, dict):
        return None

    obrigatorios = set(entrada.get("required") or [])
    campos: dict[str, Campo] = {}
    for nome, bruto in (entrada.get("properties") or {}).items():
        if not isinstance(bruto, dict):
            continue
        no = _resolver(bruto, componentes)
        opcoes = no.get("enum")
        campos[nome] = Campo(
            nome=nome,
            tipo=no.get("type"),
            opcoes=tuple(str(o) for o in opcoes) if isinstance(opcoes, list) else None,
            obrigatorio=nome in obrigatorios,
            formato=no.get("format"),
        )
    return EsquemaModelo(modelo=modelo, versao=versao.get("id"), campos=campos)
