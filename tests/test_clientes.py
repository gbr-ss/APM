from app.models.cliente import Cliente


def test_criar_editar_buscar_e_desativar_cliente(cliente, db_session_test):
    criado = cliente.post(
        "/clientes/novo",
        data={"nome": "Ana Teste", "matricula": "A123", "telefone": "11999990000", "is_associado": "true"},
        follow_redirects=False,
    )
    assert criado.status_code == 302
    pessoa = db_session_test.query(Cliente).filter_by(matricula="A123").one()
    assert pessoa.is_associado is True

    assert "Ana Teste" in cliente.get("/clientes/", params={"busca": "Ana"}).text
    assert cliente.get(f"/clientes/{pessoa.id}/editar").status_code == 200
    editado = cliente.post(
        f"/clientes/{pessoa.id}/editar",
        data={"nome": "Ana Editada", "matricula": "A123", "telefone": "", "is_associado": "false"},
        follow_redirects=False,
    )
    assert editado.status_code == 302
    assert pessoa.nome == "Ana Editada"
    assert pessoa.is_associado is False

    cliente.post(f"/clientes/{pessoa.id}/toggle-ativo", follow_redirects=False)
    assert pessoa.ativo is False


def test_clientes_filtram_por_matricula_e_associacao_e_ordenam_nome(
    cliente, db_session_test
):
    db_session_test.add_all(
        [
            Cliente(nome="Zeca Associado", matricula="MAT-Z", is_associado=True),
            Cliente(nome="Ana Associada", matricula="MAT-A", is_associado=True),
            Cliente(nome="Bruno Visitante", matricula="MAT-B", is_associado=False),
        ]
    )
    db_session_test.commit()

    associados = cliente.get("/clientes/", params={"apenas_associados": "true"})
    por_matricula = cliente.get("/clientes/", params={"busca": "MAT-B"})

    assert "Ana Associada" in associados.text
    assert "Zeca Associado" in associados.text
    assert "Bruno Visitante" not in associados.text
    assert associados.text.index("Ana Associada") < associados.text.index("Zeca Associado")
    assert "Bruno Visitante" in por_matricula.text
    assert "Ana Associada" not in por_matricula.text


def test_cliente_rejeita_matricula_duplicada(cliente):
    dados = {"nome": "Primeiro", "matricula": "M-1", "telefone": "", "is_associado": "false"}
    assert cliente.post("/clientes/novo", data=dados, follow_redirects=False).status_code == 302
    duplicado = cliente.post(
        "/clientes/novo",
        data={**dados, "nome": "Segundo"},
    )
    assert duplicado.status_code == 400


def test_edicao_de_cliente_rejeita_matricula_de_outro_cliente(
    cliente, db_session_test
):
    alvo = Cliente(nome="Cliente A", matricula="A-1")
    outro = Cliente(nome="Cliente B", matricula="B-1")
    db_session_test.add_all([alvo, outro])
    db_session_test.commit()

    response = cliente.post(
        f"/clientes/{alvo.id}/editar",
        data={"nome": "Cliente A", "matricula": "B-1"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "erro=matricula" in response.headers["location"]
    assert alvo.matricula == "A-1"


def test_lista_de_clientes_pagina_resultados_e_preserva_filtros(
    cliente, db_session_test
):
    db_session_test.add_all(
        [
            Cliente(
                nome=f"Cliente {numero:02}",
                matricula=f"MAT-{numero:02}",
                is_associado=numero < 11,
            )
            for numero in range(12)
        ]
    )
    db_session_test.commit()

    primeira = cliente.get("/clientes/", params={"page": 1})
    segunda = cliente.get("/clientes/", params={"page": 2})
    associados_pagina_1 = cliente.get(
        "/clientes/",
        params={"busca": "Cliente", "apenas_associados": "true", "page": 1},
    )
    associados_pagina_2 = cliente.get(
        "/clientes/",
        params={"busca": "Cliente", "apenas_associados": "true", "page": 2},
    )

    assert "Cliente 00" in primeira.text
    assert "Cliente 09" in primeira.text
    assert "Cliente 10" not in primeira.text
    assert "Cliente 10" in segunda.text
    assert "Cliente 11" in segunda.text

    assert "Cliente 09" in associados_pagina_1.text
    assert "Cliente 10" not in associados_pagina_1.text
    assert "Cliente 10" in associados_pagina_2.text
    assert "Cliente 11" not in associados_pagina_2.text
    assert "apenas_associados=true" in associados_pagina_2.text
    assert "page=1" in associados_pagina_2.text
