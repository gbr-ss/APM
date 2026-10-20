from app.models.categoria import Categoria
from app.models.produto import Produto


def test_editar_e_desativar_produto(cliente, db_session_test):
    produto = Produto(nome="Caderno", preco=12.5, estoque_atual=5, ativo=True)
    db_session_test.add(produto)
    db_session_test.commit()

    assert cliente.get(f"/produtos/{produto.id}").status_code == 200
    assert cliente.get(f"/produtos/{produto.id}/editar").status_code == 200
    editado = cliente.post(
        f"/produtos/{produto.id}/editar",
        data={"nome": "Caderno Grande", "preco": "18.50", "estoque_atual": "8", "categoria_id": "0"},
        follow_redirects=False,
    )
    assert editado.status_code == 302
    assert produto.nome == "Caderno Grande"
    assert produto.preco == 18.5
    assert produto.estoque_atual == 8

    desativado = cliente.post(f"/produtos/{produto.id}/desativar", follow_redirects=False)
    assert desativado.status_code == 302
    assert produto.ativo is False
    assert cliente.get(f"/produtos/{produto.id}", follow_redirects=False).status_code == 302


def test_criar_produto_rejeita_nome_duplicado(cliente, db_session_test):
    db_session_test.add(Produto(nome="Garrafa", preco=20, estoque_atual=4))
    db_session_test.commit()

    response = cliente.post(
        "/produtos/novo",
        data={"nome": "Garrafa", "preco": "25", "estoque_atual": "3", "categoria_id": "0"},
    )

    assert response.status_code == 400
    assert db_session_test.query(Produto).count() == 1


def test_listagem_de_produtos_retorna_200(cliente):
    response = cliente.get("/produtos/")
    assert response.status_code == 200


def test_listagem_de_produtos_exibe_produto_cadastrado(db_session_test, cliente):
    categoria = Categoria(nome="Bon?s")
    db_session_test.add(categoria)
    db_session_test.flush()
    db_session_test.add(Produto(nome="Bon? AAPM", preco=35.0, estoque_atual=10, categoria_id=categoria.id))
    db_session_test.commit()

    response = cliente.get("/produtos/")

    assert response.status_code == 200
    assert "Bon? AAPM" in response.text


def test_busca_de_produtos_filtra_por_nome(db_session_test, cliente):
    db_session_test.add_all([
        Produto(nome="Caneca AAPM", preco=20.0, estoque_atual=5),
        Produto(nome="Camiseta Escolar", preco=40.0, estoque_atual=8),
    ])
    db_session_test.commit()

    response = cliente.get("/produtos/", params={"busca": "Caneca"})

    assert response.status_code == 200
    assert "Caneca AAPM" in response.text
    assert "Camiseta Escolar" not in response.text


def test_criar_produto_redireciona_e_persiste(cliente, db_session_test):
    response = cliente.post(
        "/produtos/novo",
        data={"nome": "Garrafa AAPM", "preco": "24.90", "estoque_atual": "6"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/produtos?criado=ok"
    produto = db_session_test.query(Produto).filter_by(nome="Garrafa AAPM").first()
    assert produto is not None
    assert produto.preco == 24.9
    assert produto.estoque_atual == 6
