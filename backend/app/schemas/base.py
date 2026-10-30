"""Base dos schemas Pydantic.

O JSON da API usa **camelCase** para coincidir com os tipos que o aplicativo já tem em
`src/data/tipos.ts`. Assim a integração não precisa de uma camada de tradução de nomes,
que seria mais código e mais chance de erro. Internamente os campos seguem snake_case.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ModeloBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


#: Faixa aceita para a duração de um agendamento ou de um atendimento, em minutos. A mesma
#: faixa está na restrição do banco e no aplicativo (`src/utils/duracao.ts`).
DURACAO_MINIMA = 15
DURACAO_MAXIMA = 480

#: Duração opcional: vazio quer dizer "não informada", nunca um valor padrão.
DuracaoOpcional = Annotated[int | None, Field(default=None, ge=DURACAO_MINIMA, le=DURACAO_MAXIMA)]
