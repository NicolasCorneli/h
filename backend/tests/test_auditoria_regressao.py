"""Regressões dos defeitos encontrados na auditoria de QA (docs/historico/RELATORIO_QA_E_MELHORIAS.md).

Cada teste reproduz um defeito que existia antes da correção: rodados contra o código
anterior, eles falham. Os de concorrência usam duas sessões de banco de verdade, porque a
corrida só existe entre transações distintas.
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select

from app.core import config as modulo_config
from app.core.erros import ValidacaoFalhou
from app.db.session import FabricaSessao, engine
from app.models import Agendamento, Atendimento, Imagem, Simulacao, StatusAgendamento, Usuario
from app.schemas.agendamento import AgendamentoEntrada, Conclusao
from app.services import agendamentos as servico_agenda
from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def _cliente(cliente_http: TestClient, cabecalhos, nome: str = "Marina Alves") -> dict:
    resposta = cliente_http.post("/api/v1/clientes", headers=cabecalhos, json={"nome": nome})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _agendamento_direto(usuario: Usuario, cliente, dias: int = 1) -> uuid.UUID:
    with FabricaSessao() as s:
        registro = Agendamento(
            cliente_id=cliente.id,
            usuario_id=usuario.id,
            data_hora=datetime.now(UTC) + timedelta(days=dias),
            servico="Corte",
        )
        s.add(registro)
        s.commit()
        return registro.id


# --- Concorrência na agenda ---------------------------------------------------


def test_conclusao_simultanea_devolve_o_mesmo_atendimento(usuario_direto, cliente_direto):
    """Antes: a segunda conclusão decidia pelo status lido antes da trava e batia no índice
    único, virando erro 500 em vez da resposta idempotente."""
    usuario = usuario_direto()
    agendamento_id = _agendamento_direto(usuario, cliente_direto(usuario))

    with FabricaSessao() as tardia, FabricaSessao() as primeira:
        # A requisição "tardia" já leu o agendamento (pendente) antes de a outra concluir.
        lido_antes = tardia.get(Agendamento, agendamento_id)
        usuario_tardio = tardia.get(Usuario, usuario.id)
        assert lido_antes.status is StatusAgendamento.pendente

        criado = servico_agenda.concluir(
            primeira,
            primeira.get(Usuario, usuario.id),
            primeira.get(Agendamento, agendamento_id),
            Conclusao(),
        )
        repetido = servico_agenda.concluir(tardia, usuario_tardio, lido_antes, Conclusao())

    assert repetido.id == criado.id
    with FabricaSessao() as s:
        total = s.scalar(
            select(func.count())
            .select_from(Atendimento)
            .where(Atendimento.agendamento_id == agendamento_id)
        )
    assert total == 1


def test_confirmar_nao_desfaz_um_cancelamento_simultaneo(usuario_direto, cliente_direto):
    """Antes: quem leu "pendente" antes do cancelamento confirmava por cima dele."""
    usuario = usuario_direto()
    agendamento_id = _agendamento_direto(usuario, cliente_direto(usuario))

    with FabricaSessao() as tardia, FabricaSessao() as primeira:
        lido_antes = tardia.get(Agendamento, agendamento_id)
        servico_agenda.cancelar(primeira, primeira.get(Agendamento, agendamento_id), "remarcar")
        with pytest.raises(ValidacaoFalhou) as erro:
            servico_agenda.confirmar(tardia, lido_antes)
        assert erro.value.codigo == "transicao_invalida"

    with FabricaSessao() as s:
        assert s.get(Agendamento, agendamento_id).status is StatusAgendamento.cancelado


def test_criacoes_simultaneas_nao_ocupam_o_mesmo_horario(usuario_direto, cliente_direto):
    """Antes: as duas transações conferiam o conflito antes de qualquer commit e as duas
    gravavam o mesmo horário. Agora a segunda espera a primeira e é recusada."""
    usuario = usuario_direto()
    cliente = cliente_direto(usuario)
    dados = AgendamentoEntrada(
        cliente_id=cliente.id,
        data_hora=datetime.now(UTC) + timedelta(days=2),
        servico="Corte",
        duracao_min=60,
    )
    resultado: dict[str, object] = {}

    def segunda():
        with FabricaSessao() as s:
            try:
                servico_agenda.criar(s, s.get(Usuario, usuario.id), dados)
                resultado["segunda"] = "criou"
            except ValidacaoFalhou as erro:
                resultado["segunda"] = erro.codigo

    with FabricaSessao() as primeira:
        commit_real = primeira.commit
        linha = threading.Thread(target=segunda)

        def commit_com_concorrente():
            # A segunda requisição chega enquanto a primeira ainda não gravou.
            linha.start()
            time.sleep(0.5)
            resultado["segunda_esperou"] = linha.is_alive()
            commit_real()

        primeira.commit = commit_com_concorrente  # type: ignore[method-assign]
        servico_agenda.criar(primeira, primeira.get(Usuario, usuario.id), dados)
        linha.join(timeout=10)

    assert resultado["segunda_esperou"] is True
    assert resultado["segunda"] == "horario_ocupado"
    with FabricaSessao() as s:
        total = s.scalar(
            select(func.count()).select_from(Agendamento).where(Agendamento.usuario_id == usuario.id)
        )
    assert total == 1


# --- Datas do histórico e do cadastro -------------------------------------------


def test_atendimento_avulso_no_futuro_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    amanha = (date.today() + timedelta(days=2)).isoformat()
    resposta = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={"clienteId": c["id"], "descricao": "Corte", "dataServico": amanha},
    )
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["erro"]["codigo"] == "atendimento_no_futuro"


def test_corrigir_a_data_do_atendimento_para_o_futuro_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={"clienteId": c["id"], "descricao": "Corte", "dataServico": "2026-01-10"},
    ).json()
    resposta = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}",
        headers=cabecalhos,
        json={"dataServico": (date.today() + timedelta(days=30)).isoformat()},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "atendimento_no_futuro"


def test_corrigir_o_dia_descarta_o_horario_de_outro_dia(cliente_http: TestClient, conta):
    """Antes: o registro ficava com `dataServico` de um dia e `realizadoEm` de outro."""
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": c["id"],
            "descricao": "Escova",
            "realizadoEm": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        },
    ).json()
    assert atendimento["realizadoEm"] is not None

    corrigido = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}",
        headers=cabecalhos,
        json={"dataServico": "2026-01-10"},
    ).json()
    assert corrigido["dataServico"] == "2026-01-10"
    assert corrigido["realizadoEm"] is None

    # Sem mudar o dia, nada se perde.
    mantido = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}",
        headers=cabecalhos,
        json={"dataServico": "2026-01-10", "observacoes": "nota"},
    ).json()
    assert mantido["observacoes"] == "nota"


@pytest.mark.parametrize("nascimento", ["2099-01-01", "1800-05-05"])
def test_edicao_do_cliente_valida_o_nascimento(cliente_http: TestClient, conta, nascimento):
    """Antes: a regra valia só no cadastro; o PATCH gravava qualquer data."""
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    resposta = cliente_http.patch(
        f"/api/v1/clientes/{c['id']}", headers=cabecalhos, json={"dataNascimento": nascimento}
    )
    assert resposta.status_code == 422, resposta.text
    assert cliente_http.get(f"/api/v1/clientes/{c['id']}", headers=cabecalhos).json()[
        "dataNascimento"
    ] is None


def test_historico_do_mesmo_dia_vem_do_mais_recente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    base = datetime.now(UTC).replace(hour=15, minute=0, second=0, microsecond=0) - timedelta(days=3)
    for horas, descricao in ((0, "Manhã"), (3, "Tarde"), (1, "Meio-dia")):
        cliente_http.post(
            "/api/v1/atendimentos",
            headers=cabecalhos,
            json={
                "clienteId": c["id"],
                "descricao": descricao,
                "realizadoEm": (base + timedelta(hours=horas)).isoformat(),
            },
        )
    historico = cliente_http.get(f"/api/v1/clientes/{c['id']}/historico", headers=cabecalhos).json()
    assert [a["descricao"] for a in historico] == ["Tarde", "Meio-dia", "Manhã"]


# --- Entradas ------------------------------------------------------------------


def test_busca_trata_curingas_como_texto(cliente_http: TestClient, conta):
    """Antes: buscar "_" ou "%" devolvia a carteira inteira."""
    cabecalhos, _ = conta()
    _cliente(cliente_http, cabecalhos, "Ana Souza")
    _cliente(cliente_http, cabecalhos, "Bruno_Lima")
    _cliente(cliente_http, cabecalhos, "Carla 50% Silva")

    def buscar(texto: str) -> list[str]:
        resposta = cliente_http.get("/api/v1/clientes", headers=cabecalhos, params={"busca": texto})
        return [c["nome"] for c in resposta.json()]

    assert buscar("_") == ["Bruno_Lima"]
    assert buscar("%") == ["Carla 50% Silva"]
    assert buscar("ana") == ["Ana Souza"]


def test_atuacao_vazia_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.patch("/api/v1/usuarios/me", headers=cabecalhos, json={"atuacao": "  "})
    assert resposta.status_code == 422
    assert cliente_http.get("/api/v1/usuarios/me", headers=cabecalhos).json()["atuacao"]


# --- Produção --------------------------------------------------------------------


def test_producao_nao_sobe_com_modo_demonstracao(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("MODO_DEMO", "true")
    with pytest.raises(ValueError, match="MODO_DEMO"):
        modulo_config.Configuracao()


def test_seed_se_recusa_em_producao(monkeypatch: pytest.MonkeyPatch, sessao):
    """As contas de demonstração têm senha publicada: em produção seriam contas abertas."""
    from app import seed

    monkeypatch.setenv("AMBIENTE", "producao")
    monkeypatch.setenv("MODO_DEMO", "false")
    monkeypatch.setenv("URL_PUBLICA", "https://api.exemplo.com.br")
    monkeypatch.setattr("sys.argv", ["seed"])
    modulo_config.obter_config.cache_clear()
    try:
        assert seed.main() == 2
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()
    assert sessao.scalar(select(Usuario).where(Usuario.email == seed.EMAIL_PRINCIPAL)) is None


# --- Imagens: exclusão durante a geração -----------------------------------------


def test_apagar_imagens_durante_a_geracao_nao_deixa_arquivo_orfao(
    cliente_http: TestClient, conta, monkeypatch: pytest.MonkeyPatch
):
    """Antes: o resultado gerado depois da exclusão era gravado no storage e, com a
    simulação já apagada, ficava no disco sem registro que o encontrasse."""
    from app.services import imagens as servico_imagens
    from app.services.ai.fake import ProvedorLocal
    from app.models import Cliente

    cabecalhos, usuario = conta()
    c = _cliente(cliente_http, cabecalhos)
    cliente_http.post(f"/api/v1/clientes/{c['id']}/consentimentos", headers=cabecalhos, json=ACEITE)

    gerar_original = ProvedorLocal.gerar

    def gerar_enquanto_apagam(self, entrada):
        # Enquanto o provedor trabalha, o profissional apaga as imagens do cliente.
        with FabricaSessao() as outra:
            servico_imagens.excluir_simulacoes_do_cliente(
                outra,
                outra.get(Usuario, uuid.UUID(usuario["id"])),
                outra.get(Cliente, uuid.UUID(c["id"])),
            )
        return gerar_original(self, entrada)

    monkeypatch.setattr(ProvedorLocal, "gerar", gerar_enquanto_apagam)
    resposta = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": c["id"], "corte": "Bob curto", "cor": "Ruivo intenso"},
        files=arquivo_de_foto(),
    )
    assert resposta.status_code == 202, resposta.text

    with FabricaSessao() as s:
        assert s.scalar(select(func.count()).select_from(Simulacao)) == 0
        assert s.scalar(select(func.count()).select_from(Imagem)) == 0
    pasta = Path(modulo_config.obter_config().storage_dir) / "usuarios" / usuario["id"]
    sobras = [p for p in pasta.rglob("*") if p.is_file()] if pasta.exists() else []
    assert sobras == [], f"arquivos órfãos no storage: {sobras}"


# --- Desempenho: número de consultas não cresce com a carteira -------------------


def _contar_consultas(funcao) -> int:
    total = 0

    def contar(*_args, **_kwargs):
        nonlocal total
        total += 1

    event.listen(engine, "before_cursor_execute", contar)
    try:
        funcao()
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    return total


def test_lista_de_clientes_e_simulacoes_sem_consulta_por_linha(cliente_http: TestClient, conta):
    """Antes: uma consulta de foto por cliente na lista, e na lista geral de simulações uma
    consulta por cliente mais duas por simulação (as imagens)."""
    cabecalhos, _ = conta()

    def acrescentar(quantidade: int) -> None:
        for _ in range(quantidade):
            c = _cliente(cliente_http, cabecalhos, f"Cliente {uuid.uuid4().hex[:6]}")
            cliente_http.post(
                f"/api/v1/clientes/{c['id']}/consentimentos", headers=cabecalhos, json=ACEITE
            )
            cliente_http.post(
                f"/api/v1/clientes/{c['id']}/foto",
                headers=cabecalhos,
                files={"arquivo": ("f.jpg", arquivo_de_foto()["foto"][1], "image/jpeg")},
            )
            cliente_http.post(
                "/api/v1/simulacoes",
                headers=cabecalhos,
                data={"clienteId": c["id"], "corte": "Bob curto", "cor": "Ruivo intenso"},
                files=arquivo_de_foto(),
            )

    def medir() -> tuple[int, int]:
        clientes = _contar_consultas(
            lambda: cliente_http.get("/api/v1/clientes", headers=cabecalhos).raise_for_status()
        )
        simulacoes = _contar_consultas(
            lambda: cliente_http.get("/api/v1/simulacoes", headers=cabecalhos).raise_for_status()
        )
        return clientes, simulacoes

    acrescentar(2)
    com_dois = medir()
    acrescentar(3)
    com_cinco = medir()
    assert com_cinco == com_dois, f"consultas cresceram com a carteira: {com_dois} -> {com_cinco}"


# --- Correção e exclusão de atendimento (o aplicativo não oferecia nenhuma) -------


def test_corrigir_dia_hora_e_duracao_do_atendimento(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": c["id"],
            "descricao": "Corte",
            "realizadoEm": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "duracaoMin": 30,
        },
    ).json()
    # 23h30 de Brasília é o dia seguinte em UTC: o dia gravado é o do salão.
    quando = "2026-10-10T02:30:00+00:00"
    corrigido = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}",
        headers=cabecalhos,
        json={"descricao": "Escova", "realizadoEm": quando, "duracaoMin": 45},
    ).json()
    assert corrigido["descricao"] == "Escova"
    assert corrigido["dataServico"] == "2026-10-09"
    assert corrigido["realizadoEm"].startswith("2026-10-10T02:30")
    assert corrigido["duracaoMin"] == 45

    # null apaga a duração; ausente não mexe.
    sem_duracao = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}", headers=cabecalhos, json={"duracaoMin": None}
    ).json()
    assert sem_duracao["duracaoMin"] is None
    assert sem_duracao["descricao"] == "Escova"

    futuro = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}",
        headers=cabecalhos,
        json={"realizadoEm": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
    )
    assert futuro.status_code == 422
    assert futuro.json()["erro"]["codigo"] == "atendimento_no_futuro"


def test_exclui_atendimento_avulso_mas_nao_o_da_agenda(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = _cliente(cliente_http, cabecalhos)
    avulso = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={"clienteId": c["id"], "descricao": "Corte", "dataServico": "2026-01-10"},
    ).json()
    assert cliente_http.delete(f"/api/v1/atendimentos/{avulso['id']}", headers=cabecalhos).status_code == 204
    assert cliente_http.get(f"/api/v1/atendimentos/{avulso['id']}", headers=cabecalhos).status_code == 404

    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": c["id"],
            "dataHora": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "servico": "Corte",
        },
    ).json()
    da_agenda = cliente_http.post(
        f"/api/v1/agendamentos/{agendamento['id']}/concluir", headers=cabecalhos, json={}
    ).json()["atendimento"]
    resposta = cliente_http.delete(f"/api/v1/atendimentos/{da_agenda['id']}", headers=cabecalhos)
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "atendimento_da_agenda"
    assert cliente_http.get(f"/api/v1/atendimentos/{da_agenda['id']}", headers=cabecalhos).status_code == 200


def test_erros_http_genericos_saem_em_portugues(cliente_http: TestClient, conta):
    """Antes: "Method Not Allowed" e "Not Found", em inglês, chegavam à tela."""
    cabecalhos, _ = conta()
    metodo_errado = cliente_http.put("/api/v1/clientes", headers=cabecalhos, json={})
    assert metodo_errado.status_code == 405
    assert metodo_errado.json()["erro"]["mensagem"] == (
        "Esta operação não está disponível nesta versão do servidor."
    )
    inexistente = cliente_http.get("/api/v1/rota-que-nao-existe", headers=cabecalhos)
    assert inexistente.status_code == 404
    assert inexistente.json()["erro"]["mensagem"] == "Endereço não encontrado."


def test_envio_em_partes_nao_e_lido_alem_do_limite(cliente_http: TestClient, conta, monkeypatch):
    """Sem `Content-Length` (envio chunked), a borda não barra; a leitura é que para."""
    import io

    from app.services import validacao_foto

    monkeypatch.setattr(modulo_config.obter_config(), "imagem_max_bytes", 1000)

    class Arquivo(io.BytesIO):
        lido = 0

        def read(self, tamanho=-1):  # noqa: D401 - imita o arquivo do upload
            dados = super().read(tamanho)
            Arquivo.lido += len(dados)
            return dados

    arquivo = Arquivo(b"x" * 50_000)
    conteudo = validacao_foto.ler_envio(arquivo)
    assert len(conteudo) == 1001
    assert Arquivo.lido == 1001
    with pytest.raises(Exception) as erro:
        validacao_foto.validar_e_normalizar(conteudo)
    assert "Arquivo muito grande" in str(erro.value.detalhes)


def test_quem_aceitou_menor_e_fez_18_revoga_sem_responsavel(cliente_http: TestClient, conta):
    """Contrato que o aplicativo passou a seguir: o responsável só vai junto enquanto o
    cliente é menor. Antes o aplicativo mandava o responsável do aceite antigo, o servidor
    recusava ("só se aplica a menor") e a revogação ficava impossível."""
    cabecalhos, _ = conta()
    hoje = date.today()
    menor = cliente_http.post(
        "/api/v1/clientes",
        headers=cabecalhos,
        json={"nome": "Lara Prado", "dataNascimento": date(hoje.year - 17, 1, 1).isoformat()},
    ).json()
    aceite = cliente_http.post(
        f"/api/v1/clientes/{menor['id']}/consentimentos",
        headers=cabecalhos,
        json={**ACEITE, "confirmadoPor": "Rita Prado", "responsavel": {"nome": "Rita Prado", "parentesco": "mãe"}},
    )
    assert aceite.status_code == 201, aceite.text
    # Um ano depois (aqui: a data corrigida), a cliente é adulta.
    cliente_http.patch(
        f"/api/v1/clientes/{menor['id']}",
        headers=cabecalhos,
        json={"dataNascimento": date(hoje.year - 19, 1, 1).isoformat()},
    )
    revogacao = cliente_http.post(
        f"/api/v1/clientes/{menor['id']}/consentimentos",
        headers=cabecalhos,
        json={"decisao": "revogado", "formaObtencao": "lido_em_voz_alta",
              "confirmadoPor": "Lara Prado", "responsavel": None, "observacao": ""},
    )
    assert revogacao.status_code == 201, revogacao.text
    assert revogacao.json()["status"] == "revogado"


def test_storage_relativo_e_resolvido_a_partir_da_pasta_backend(monkeypatch, tmp_path):
    """Antes: `./dados/imagens` dependia da pasta de onde a API era iniciada, e as fotos
    gravadas "sumiam" (404 com "objeto ausente no storage") ao iniciar de outra pasta."""
    monkeypatch.setenv("STORAGE_DIR", "./dados/imagens")
    monkeypatch.chdir(tmp_path)
    configuracao = modulo_config.Configuracao()
    assert configuracao.storage_dir == (modulo_config.RAIZ / "dados" / "imagens").resolve()
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "absoluto"))
    assert modulo_config.Configuracao().storage_dir == tmp_path / "absoluto"
