"""A carga de demonstração precisa produzir os cenários que o roteiro de testes usa."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.seed import EMAIL_PRINCIPAL, EMAIL_SECUNDARIO, SENHA_DEMO, limpar, popular

ESPERADO = {
    "Aline Barros": ("aceito", False),
    "Bruno Tavares": ("pendente", False),
    "Carla Menezes": ("recusado", False),
    "Júlia Stein": ("aceito", True),  # aceitou a versão 0.9: pede revalidação
    "Marina Alves": ("aceito", False),
    "Rafael Prado": ("revogado", False),
    "Sofia Ramires": ("aceito", False),
}


def test_seed_cria_os_cenarios(sessao, cliente_http: TestClient):
    resumo = popular(sessao)
    try:
        assert resumo.usuarios == 2
        assert resumo.clientes == 9  # 7 do profissional + 2 do colega
        assert resumo.consentimentos == 7
        assert resumo.simulacoes == 5
        assert resumo.imagens == 10  # entrada e saída de cada simulação

        entrada = cliente_http.post(
            "/api/v1/auth/login", json={"email": EMAIL_PRINCIPAL, "senha": SENHA_DEMO}
        )
        assert entrada.status_code == 200
        cabecalhos = {"Authorization": f"Bearer {entrada.json()['tokens']['accessToken']}"}

        clientes = {c["nome"]: c for c in cliente_http.get("/api/v1/clientes", headers=cabecalhos).json()}
        assert set(clientes) == set(ESPERADO)
        for nome, (status, revalidar) in ESPERADO.items():
            assert clientes[nome]["consentimento"]["status"] == status, nome
            assert clientes[nome]["consentimento"]["revalidar"] is revalidar, nome

        assert clientes["Sofia Ramires"]["consentimento"]["registro"]["responsavel"] == {
            "nome": "Denise Ramires",
            "parentesco": "Mãe",
        }

        # Rafael tem dois registros: o aceite e a revogação.
        historico = cliente_http.get(
            f"/api/v1/clientes/{clientes['Rafael Prado']['id']}/consentimentos", headers=cabecalhos
        ).json()
        assert [r["decisao"] for r in historico] == ["revogado", "aceito"]

        # Marina tem três simulações e uma preferida, com imagem que abre.
        simulacoes = cliente_http.get(
            f"/api/v1/clientes/{clientes['Marina Alves']['id']}/simulacoes", headers=cabecalhos
        ).json()
        assert len(simulacoes) == 3
        assert sum(1 for s in simulacoes if s["preferida"]) == 1
        imagem = cliente_http.get(simulacoes[0]["imgSaidaUri"].replace("http://testserver", ""))
        assert imagem.status_code == 200

        assert cliente_http.get("/api/v1/usuarios/me/ciencia", headers=cabecalhos).json()["aceita"] is True
        agendamentos = cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json()
        assert len(agendamentos) == 9
        assert any(a["duracaoMin"] is None for a in agendamentos)
        atendimentos = cliente_http.get("/api/v1/atendimentos", headers=cabecalhos).json()
        assert len(atendimentos) == 5

        # O concluído da demonstração tem o atendimento ligado a ele, e o cancelado guarda
        # o motivo: a demonstração mostra os fluxos da agenda como o aplicativo os grava.
        concluido = next(a for a in agendamentos if a["status"] == "concluido")
        ligado = next(a for a in atendimentos if a["id"] == concluido["atendimentoId"])
        assert ligado["agendamentoId"] == concluido["id"]
        assert ligado["realizadoEm"] is not None
        cancelado = next(a for a in agendamentos if a["status"] == "cancelado")
        assert cancelado["motivoCancelamento"] and cancelado["canceladoEm"]

        # A conta do colega é isolada.
        colega = cliente_http.post(
            "/api/v1/auth/login", json={"email": EMAIL_SECUNDARIO, "senha": SENHA_DEMO}
        ).json()
        cabecalhos_colega = {"Authorization": f"Bearer {colega['tokens']['accessToken']}"}
        assert len(cliente_http.get("/api/v1/clientes", headers=cabecalhos_colega).json()) == 2
        assert cliente_http.get(
            f"/api/v1/clientes/{clientes['Marina Alves']['id']}", headers=cabecalhos_colega
        ).status_code == 404
    finally:
        limpar(sessao)
