"""Termo 1.2: a foto passa pela Replicate e pelo Google (migration a9e4c2b7d158).

Confere a publicação (a 1.1 continua no banco, intacta e fora de vigência), o que o texto
novo precisa dizer, a revalidação de quem aceitou a 1.1 e o aviso de inicialização que
acusa termo e modelo desencontrados.
"""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine
from app.main import divergencia_entre_termo_e_modelo
from tests.fabricas import arquivo_de_foto
from tests.test_consentimento import novo_cliente, registrar


def termos(tipo: str) -> dict[str, dict]:
    with engine.begin() as conexao:
        linhas = conexao.execute(
            text("SELECT versao, vigente, secoes FROM termos WHERE tipo = :tipo"), {"tipo": tipo}
        ).mappings()
        return {linha["versao"]: dict(linha) for linha in linhas}


def texto_de(termo: dict) -> str:
    return " ".join(f"{s['titulo']} {s['texto']}" for s in termo["secoes"])


def test_1_2_vigente_e_1_1_preservada_para_os_dois_tipos(versao_vigente):
    for tipo in ("cliente", "profissional"):
        publicados = termos(tipo)
        # Vigente é a 1.2 ou uma revisão só de redação dela (1.2.1, sem travessões).
        assert versao_vigente(tipo).startswith("1.2"), f"termo de {tipo} não está na 1.2"
        assert publicados["1.1"]["vigente"] is False
        # O texto que os clientes anteriores leram continua lá, sem alteração.
        assert "outra empresa" in texto_de(publicados["1.1"])
        assert sum(1 for t in publicados.values() if t["vigente"]) == 1


def test_termo_do_cliente_diz_para_onde_a_foto_vai_e_o_que_pode_acontecer():
    texto = texto_de(termos("cliente")["1.2"])
    for trecho in (
        "Replicate",
        "Google",
        "o corte, o gênero do corte e a cor",
        "treinar",
        "cerca de uma hora",
        "fora do Brasil",
        "não é público",
        "recuse",
        "marca invisível",
    ):
        assert trecho in texto, f"o termo 1.2 não diz: {trecho}"
    for dado in ("nome", "telefone", "data de nascimento", "observações"):
        assert dado in texto, f"o termo 1.2 não diz que {dado} fica de fora"
    assert "outra empresa" not in texto, "o termo ainda fala de uma empresa só"


def test_termo_do_profissional_manda_explicar_as_duas_empresas():
    texto = texto_de(termos("profissional")["1.2"])
    assert "Replicate" in texto and "Google" in texto and "treinar" in texto


def test_aceite_sobre_a_1_1_exige_revalidacao_antes_da_proxima_foto(cliente_http: TestClient, conta, versao_vigente):
    """Quem aceitou a 1.1 precisa decidir de novo, já sabendo do Google."""
    cabecalhos, _ = conta()
    atual = versao_vigente()
    cliente = novo_cliente(cliente_http, cabecalhos)

    # Volta a vigência à 1.1 só para registrar um aceite sobre ela, como em produção.
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'cliente' AND versao = :v"), {"v": atual})
        conexao.execute(text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = '1.1'"))
    try:
        assert registrar(cliente_http, cabecalhos, cliente["id"]).status_code == 201
    finally:
        with engine.begin() as conexao:
            conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'cliente' AND versao = '1.1'"))
            conexao.execute(text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = :v"), {"v": atual})

    resumo = cliente_http.get(f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos).json()
    assert resumo["status"] == "aceito"
    assert resumo["revalidar"] is True
    assert resumo["versaoVigente"] == atual

    bloqueada = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": "Chanel", "cor": "Ruivo", "observacoes": ""},
        files=arquivo_de_foto(),
    )
    assert bloqueada.status_code == 403
    assert bloqueada.json()["erro"]["detalhes"][0]["motivo"] == "revalidar"

    # Apresentado o 1.2, a captura volta a ser permitida.
    assert registrar(cliente_http, cabecalhos, cliente["id"]).status_code == 201
    liberada = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": "Chanel", "cor": "Ruivo", "observacoes": ""},
        files=arquivo_de_foto(),
    )
    assert liberada.status_code == 202, liberada.text


def configuracao(estrategia: str, texto: str = "black-forest-labs/flux-kontext-pro", provedor="replicate"):
    return SimpleNamespace(
        ai_provider=provedor,
        ai_estrategia=estrategia,
        ai_modelo="flux-kontext-apps/change-haircut",
        ai_modelo_texto=texto,
    )


def test_aviso_quando_o_nano_e_ligado_sem_o_termo_1_2():
    textos_1_1 = [texto_de(termos("cliente")["1.1"])]
    assert divergencia_entre_termo_e_modelo(configuracao("instrucao", "google/nano-banana-2.1"), textos_1_1)


def test_aviso_quando_se_volta_ao_kontext_com_o_termo_1_2():
    textos_1_2 = [texto_de(termos("cliente")["1.2"])]
    assert divergencia_entre_termo_e_modelo(configuracao("especializado"), textos_1_2)


def test_sem_aviso_quando_termo_e_modelo_batem():
    textos_1_1 = [texto_de(termos("cliente")["1.1"])]
    textos_1_2 = [texto_de(termos("cliente")["1.2"])]
    assert divergencia_entre_termo_e_modelo(configuracao("instrucao", "google/nano-banana-2.1"), textos_1_2) is None
    assert divergencia_entre_termo_e_modelo(configuracao("especializado"), textos_1_1) is None
    # Provedor local: nada sai do sistema, não há o que comparar.
    assert divergencia_entre_termo_e_modelo(configuracao("especializado", provedor="fake"), textos_1_2) is None
