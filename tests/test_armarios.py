from app.models.armario import AluguelArmario, Armario
from app.models.cliente import Cliente


def test_ciclo_de_aluguel_de_armario(cliente, db_session_test):
    pessoa = Cliente(nome="Aluno armário", matricula="ARM-1", is_associado=False, ativo=True)
    armario = Armario(numero="A-01", descricao="Bloco A", status="disponivel")
    db_session_test.add_all([pessoa, armario])
    db_session_test.commit()

    assert "A-01" in cliente.get("/armarios/", params={"busca": "A-01"}).text
    assert cliente.get(f"/armarios/{armario.id}/editar").status_code == 200
    assert cliente.get(f"/armarios/{armario.id}/alugar").status_code == 200

    alugado = cliente.post(
        f"/armarios/{armario.id}/alugar",
        data={"cliente_id": pessoa.id, "dia": "2026-10-20", "hora": "08:30"},
        follow_redirects=False,
    )
    assert alugado.headers["location"] == "/armarios?alugado=ok"
    assert armario.status == "alugado"
    assert armario.cliente_id == pessoa.id
    assert db_session_test.query(AluguelArmario).count() == 1
    assert cliente.get("/armarios/historico").status_code == 200

    devolvido = cliente.post(f"/armarios/{armario.id}/devolver", follow_redirects=False)
    assert devolvido.headers["location"] == "/armarios?devolvido=ok"
    assert armario.status == "disponivel"
    aluguel = db_session_test.query(AluguelArmario).one()
    assert aluguel.devolvido_em is not None


def test_armario_rejeita_duplicado_status_invalido_e_aluguel_sem_cliente(cliente, db_session_test):
    armario = Armario(numero="B-01", status="disponivel")
    db_session_test.add(armario)
    db_session_test.commit()

    duplicado = cliente.post("/armarios/novo", data={"numero": "B-01", "status_armario": "disponivel"})
    status_invalido = cliente.post(
        f"/armarios/{armario.id}/status",
        data={"status_armario": "inexistente"},
        follow_redirects=False,
    )
    aluguel_invalido = cliente.post(
        f"/armarios/{armario.id}/alugar",
        data={"cliente_id": "999", "dia": "2026-10-20", "hora": "08:30"},
        follow_redirects=False,
    )

    assert duplicado.status_code == 400
    assert status_invalido.headers["location"] == "/armarios?erro=status"
    assert aluguel_invalido.headers["location"].endswith("erro=cliente")
    assert armario.status == "disponivel"


def test_criar_editar_e_alterar_status_de_armario(cliente, db_session_test):
    criado = cliente.post(
        "/armarios/novo",
        data={"numero": "C-01", "descricao": "Bloco C", "status_armario": "disponivel"},
        follow_redirects=False,
    )
    armario = db_session_test.query(Armario).filter_by(numero="C-01").one()
    assert criado.status_code == 302

    editado = cliente.post(
        f"/armarios/{armario.id}/editar",
        data={"numero": "C-02", "descricao": "Bloco novo", "status_armario": "manutencao"},
        follow_redirects=False,
    )
    assert editado.status_code == 302
    assert armario.numero == "C-02"
    assert armario.descricao == "Bloco novo"
    assert armario.status == "manutencao"

    alterado = cliente.post(
        f"/armarios/{armario.id}/status",
        data={"status_armario": "bloqueado"},
        follow_redirects=False,
    )
    assert alterado.headers["location"] == "/armarios?status=ok"
    assert armario.status == "bloqueado"

    vazio = cliente.post(
        "/armarios/novo",
        data={"numero": " ", "status_armario": "disponivel"},
    )
    assert vazio.status_code == 400
    assert db_session_test.query(Armario).count() == 1


def test_armario_alugado_bloqueia_edicao_status_e_devolucao_invalida(
    cliente, db_session_test
):
    armario = Armario(numero="D-01", status="alugado")
    db_session_test.add(armario)
    db_session_test.commit()

    edicao = cliente.post(
        f"/armarios/{armario.id}/editar",
        data={"numero": "D-02", "descricao": "", "status_armario": "disponivel"},
        follow_redirects=False,
    )
    status = cliente.post(
        f"/armarios/{armario.id}/status",
        data={"status_armario": "disponivel"},
        follow_redirects=False,
    )
    devolucao = cliente.post("/armarios/999/devolver", follow_redirects=False)

    assert edicao.status_code == status.status_code == devolucao.status_code == 302
    assert "erro=status" in edicao.headers["location"]
    assert status.headers["location"] == "/armarios?erro=alugado"
    assert devolucao.headers["location"] == "/armarios?erro=devolucao"
    assert armario.numero == "D-01"
    assert armario.status == "alugado"
