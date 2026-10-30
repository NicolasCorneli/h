"""Proteções de borda: cabeçalhos, tamanho do corpo, força bruta e custo.

São defesas simples e proporcionais ao porte do sistema. Nenhuma delas substitui as
validações de domínio; elas apenas evitam que o servidor gaste recurso — ou dinheiro —
com requisições que já se sabe que não devem prosseguir.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import obter_config
from app.core.erros import ErroDeNegocio

log = logging.getLogger(__name__)

#: Folga sobre o limite da imagem (8 MB) para caber o restante do formulário.
LIMITE_CORPO_BYTES = 12 * 1024 * 1024

#: Tentativas de autenticação por origem, dentro da janela.
MAX_TENTATIVAS = 10
JANELA_S = 300

ROTAS_LIMITADAS = (
    "/api/v1/auth/login",
    "/api/v1/auth/registrar",
    "/api/v1/auth/google",
    # Quem tem um token roubado não pode testar senhas à vontade para trocá-la.
    "/api/v1/usuarios/me/senha",
)

#: Registro em memória, por origem. Fora do objeto do middleware para poder ser zerado
#: entre os testes.
_tentativas: dict[str, deque[float]] = defaultdict(deque)

#: Acima deste número de origens guardadas, as que já saíram da janela são descartadas.
#: Sem a faxina, cada endereço que errasse uma senha ficava na memória para sempre.
MAX_ORIGENS_GUARDADAS = 10_000


def _faxinar(agora: float) -> None:
    vencidas = [
        origem for origem, marcas in _tentativas.items() if not marcas or agora - marcas[-1] > JANELA_S
    ]
    for origem in vencidas:
        del _tentativas[origem]

#: Janela do teto de simulações.
JANELA_SIMULACOES_S = 3600


def limpar_tentativas() -> None:
    _tentativas.clear()


class LimiteDeSimulacoes(ErroDeNegocio):
    """429 — a conta atingiu o teto de gerações da janela."""

    status = 429
    codigo = "limite_de_simulacoes"


def conferir_cota_de_simulacoes(sessao, usuario_id: uuid.UUID, *, travar: bool = False) -> None:
    """Recusa com 429 quando a conta já gerou o teto de simulações na última hora.

    Cada geração é uma chamada paga ao provedor externo. Autenticação não protege contra
    isso: o abuso vem de dentro de uma sessão legítima (uma conta em laço, ou um token
    roubado), e o prejuízo é o crédito contratado, não o dado. Por isso o teto é por conta.

    A contagem vem do banco (simulações criadas na última hora), e não da memória do
    processo: sobrevive a reinícios do servidor e vale para mais de um processo. Só conta
    o que foi de fato ao provedor; foto recusada ou cliente sem autorização não gastam a
    cota. Chamada duas vezes: antes de ler a foto (barata, sem trava) e logo antes de criar
    a simulação, com `travar=True`, que segura a linha da conta até o fim da transação e
    impede que duas requisições simultâneas passem juntas do teto.
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select

    from app.models import Simulacao, Usuario

    config = obter_config()
    if travar:
        sessao.execute(select(Usuario.id).where(Usuario.id == usuario_id).with_for_update())
    desde = datetime.now(UTC) - timedelta(seconds=JANELA_SIMULACOES_S)
    feitas = sessao.scalar(
        select(func.count())
        .select_from(Simulacao)
        .where(Simulacao.usuario_id == usuario_id, Simulacao.criado_em >= desde)
    )
    if feitas >= config.simulacao_max_por_hora:
        log.warning(
            "teto de simulações atingido: usuario=%s teto=%s",
            usuario_id,
            config.simulacao_max_por_hora,
        )
        raise LimiteDeSimulacoes(
            f"Você já fez {config.simulacao_max_por_hora} "
            f"{'simulação' if config.simulacao_max_por_hora == 1 else 'simulações'} na última hora, "
            "o limite desta conta. Espere um pouco antes de gerar outra.",
        )


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    """Cabeçalhos que instruem o navegador a não facilitar ataques conhecidos.

    Nenhum deles protege a API de um cliente mal-intencionado — um `curl` ignora todos.
    Eles protegem o navegador de quem usa o aplicativo na versão web, e custam uma linha
    cada:

    - `nosniff`: o navegador respeita o `Content-Type` em vez de adivinhá-lo. Sem isso,
      uma imagem enviada por terceiro poderia ser interpretada como script;
    - `DENY` no enquadramento: nenhuma página de fora pode embutir a aplicação em um
      quadro, o que elimina a classe de ataque de sobreposição de cliques;
    - `no-referrer`: nenhum endereço interno vaza para terceiros pela navegação. As URLs
      de imagem levam assinatura, então isso é mais que cosmético;
    - HSTS, só em produção: em desenvolvimento o servidor roda em HTTP e fixar a
      exigência de HTTPS no navegador atrapalharia o trabalho local.

    O cabeçalho `Server` é sobrescrito para não anunciar qual servidor de aplicação está
    em uso: é informação que só interessa a quem procura vulnerabilidade conhecida.
    """

    async def dispatch(self, request: Request, chamar_proximo):
        resposta = await chamar_proximo(request)
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        resposta.headers["Server"] = "espelho"
        if obter_config().producao:
            resposta.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return resposta


class LimiteDeCorpo(BaseHTTPMiddleware):
    """Recusa corpos grandes antes de o servidor armazená-los em disco temporário."""

    async def dispatch(self, request: Request, chamar_proximo):
        tamanho = request.headers.get("content-length")
        if tamanho and tamanho.isdigit() and int(tamanho) > LIMITE_CORPO_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "erro": {
                        "codigo": "corpo_grande_demais",
                        "mensagem": "O arquivo enviado passa do limite aceito.",
                    }
                },
            )
        return await chamar_proximo(request)


class LimiteDeTentativas(BaseHTTPMiddleware):
    """Freio simples contra força bruta no login, em memória.

    Guarda os instantes das tentativas por endereço de origem. É proporcional ao porte do
    sistema: um processo, um servidor. Em uma implantação com várias réplicas, o mesmo
    papel caberia a um serviço compartilhado (Redis) ou ao proxy de borda — está
    registrado como limitação na documentação.
    """

    async def dispatch(self, request: Request, chamar_proximo):
        if request.method != "POST" or request.url.path not in ROTAS_LIMITADAS:
            return await chamar_proximo(request)

        # Atrás de um proxy, `client.host` só é o endereço de quem chamou se o uvicorn
        # confiar nos cabeçalhos do proxy (`FORWARDED_ALLOW_IPS`; ver DEPLOY.md). Sem
        # isso, todos dividiriam o endereço do proxy, e a cota.
        origem = request.client.host if request.client else "desconhecida"
        agora = time.monotonic()
        if len(_tentativas) > MAX_ORIGENS_GUARDADAS:
            _faxinar(agora)
        marcas = _tentativas[origem]
        while marcas and agora - marcas[0] > JANELA_S:
            marcas.popleft()

        if len(marcas) >= MAX_TENTATIVAS:
            log.warning("limite de tentativas atingido: origem=%s rota=%s", origem, request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "erro": {
                        "codigo": "tentativas_demais",
                        "mensagem": "Tentativas demais. Espere alguns minutos e tente de novo.",
                    }
                },
                headers={"Retry-After": str(JANELA_S)},
            )

        resposta = await chamar_proximo(request)
        # Só conta o que falhou: quem entra corretamente não gasta a cota.
        if resposta.status_code >= 400:
            marcas.append(agora)
        elif not marcas:
            # Origem sem falha na janela: não precisa ocupar memória.
            _tentativas.pop(origem, None)
        return resposta
