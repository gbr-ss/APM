from app.models.categoria import Categoria
from app.models.produto import Produto


def test_criar_editar_e_alternar_categoria(cliente, db_session_test):
    criada = cliente.post("/categorias/nova", data={"nome": "Lanches"}, follow_redirects=False)
    assert criada.status_code == 302
    categoria = db_session_test.query(Categoria).filter_by(nome="Lanches").one()

    assert cliente.get(f"/categorias/{categoria.id}/editar").status_code == 200
    editada = cliente.post(
        f"/categorias/{categoria.id}/editar",
        data={"nome": "Alimentos"},
        follow_redirects=False,
    )
    assert editada.status_code == 302
    assert categoria.nome == "Alimentos"

    cliente.post(f"/categorias/{categoria.id}/toggle-ativo", follow_redirects=False)
    assert categoria.ativo is False


def test_categoria_vinculada_a_produto_ativo_nao_pode_ser_desativada(
    cliente, db_session_test
):
    categoria = Categoria(nome="Uniformes")
    db_session_test.add(categoria)
    db_session_test.flush()
    db_session_test.add(Produto(nome="Camiseta vinculada", preco=20, estoque_atual=2, categoria_id=categoria.id))
    db_session_test.commit()

    response = cliente.post(f"/categorias/{categoria.id}/toggle-ativo", follow_redirects=False)

    assert response.headers["location"].startswith("/categorias?erro=produtos_vinculados")
    assert categoria.ativo is True


def test_categorias_exibem_categoria_cadastrada(db_session_test, cliente):
    db_session_test.add(Categoria(nome="Lanches"))
    db_session_test.commit()

    response = cliente.get("/categorias/")

    assert response.status_code == 200
    assert "Lanches" in response.text


def test_listar_categorias_retorna_200(cliente):
    response = cliente.get("/categorias/")
    assert response.status_code == 200


def test_criar_categoria_redireciona_e_salva_no_banco(cliente, db_session_test):
    response = cliente.post(
        "/categorias/nova",
        data={"nome": "Material escolar"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/categorias?criado=ok"
    assert db_session_test.query(Categoria).filter_by(nome="Material escolar").first() is not None


def test_busca_categoria_filtra_resultado(db_session_test, cliente):
    db_session_test.add_all([
        Categoria(nome="Lanches"),
        Categoria(nome="Uniformes"),
    ])
    db_session_test.commit()

    response = cliente.get("/categorias/", params={"busca": "Lanches"})

    assert response.status_code == 200
    assert "Lanches" in response.text
    assert "Uniformes" not in response.text


def test_categoria_rejeita_nome_duplicado_no_cadastro_e_edicao(cliente, db_session_test):
    categorias = [Categoria(nome="Bebidas"), Categoria(nome="Lanches")]
    db_session_test.add_all(categorias)
    db_session_test.commit()
    bebidas, lanches = categorias

    cadastro = cliente.post("/categorias/nova", data={"nome": bebidas.nome})
    edicao = cliente.post(
        f"/categorias/{lanches.id}/editar", data={"nome": bebidas.nome}
    )

    assert cadastro.status_code == edicao.status_code == 400
    assert lanches.nome == "Lanches"
