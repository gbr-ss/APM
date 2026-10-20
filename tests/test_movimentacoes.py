from app.models.movimentacao import Movimentacao, Tipo_de_movimentacao
from app.models.produto import Produto
from app.models.produto_tamanho import ProdutoTamanho


def test_movimentacoes_de_entrada_saida_e_historico(cliente, db_session_test):
    produto = Produto(nome="Lápis", preco=2, estoque_atual=5, ativo=True)
    db_session_test.add(produto)
    db_session_test.commit()

    entrada = cliente.post(
        "/movimentacoes/nova",
        data={"produto_id": produto.id, "tipo": "entrada", "quantidade": "3", "preco_unitario": "2.50"},
        follow_redirects=False,
    )
    assert entrada.status_code == 302
    assert produto.estoque_atual == 8

    saida = cliente.post(
        "/movimentacoes/nova",
        data={"produto_id": produto.id, "tipo": "saida", "quantidade": "2", "preco_unitario": "2.50"},
        follow_redirects=False,
    )
    assert saida.status_code == 302
    assert produto.estoque_atual == 6
    assert db_session_test.query(Movimentacao).count() == 2
    assert cliente.get("/movimentacoes/", params={"tipo": "entrada"}).status_code == 200
    assert cliente.get(f"/movimentacoes/produto/{produto.id}").status_code == 200


def test_movimentacao_rejeita_tipo_quantidade_e_saida_sem_estoque(cliente, db_session_test):
    produto = Produto(nome="Borracha", preco=3, estoque_atual=1, ativo=True)
    db_session_test.add(produto)
    db_session_test.commit()
    dados = {"produto_id": produto.id, "quantidade": "1", "preco_unitario": "3"}

    tipo_invalido = cliente.post("/movimentacoes/nova", data={**dados, "tipo": "transferencia"})
    quantidade_invalida = cliente.post("/movimentacoes/nova", data={**dados, "tipo": "entrada", "quantidade": "0"})
    sem_estoque = cliente.post("/movimentacoes/nova", data={**dados, "tipo": "saida", "quantidade": "2"})

    assert tipo_invalido.status_code == 400
    assert quantidade_invalida.status_code == 400
    assert sem_estoque.status_code == 400
    assert produto.estoque_atual == 1
    assert db_session_test.query(Movimentacao).count() == 0


def test_movimentacoes_atualizam_estoque_por_tamanho_e_validam_tamanho(
    cliente, db_session_test
):
    produto = Produto(nome="Uniforme", preco=25, estoque_atual=5)
    tamanho_p = ProdutoTamanho(tamanho="P", estoque=2)
    tamanho_m = ProdutoTamanho(tamanho="M", estoque=3)
    produto.tamanhos.extend([tamanho_p, tamanho_m])
    db_session_test.add(produto)
    db_session_test.commit()

    tamanho_invalido = cliente.post(
        "/movimentacoes/nova",
        data={
            "produto_id": produto.id,
            "tamanho_id": "999",
            "tipo": "entrada",
            "quantidade": "1",
            "preco_unitario": "25",
        },
    )
    saida_excessiva = cliente.post(
        "/movimentacoes/nova",
        data={
            "produto_id": produto.id,
            "tamanho_id": tamanho_p.id,
            "tipo": "saida",
            "quantidade": "3",
            "preco_unitario": "25",
        },
    )
    entrada = cliente.post(
        "/movimentacoes/nova",
        data={
            "produto_id": produto.id,
            "tamanho_id": tamanho_m.id,
            "tipo": "entrada",
            "quantidade": "2",
            "preco_unitario": "25",
        },
        follow_redirects=False,
    )

    db_session_test.refresh(produto)
    db_session_test.refresh(tamanho_m)
    assert tamanho_invalido.status_code == saida_excessiva.status_code == 400
    assert entrada.status_code == 302
    assert tamanho_p.estoque == 2
    assert tamanho_m.estoque == 5
    assert produto.estoque_atual == 7


def test_movimentacao_de_produto_inexistente_redireciona(cliente):
    response = cliente.post(
        "/movimentacoes/nova",
        data={
            "produto_id": "999",
            "tipo": "entrada",
            "quantidade": "1",
            "preco_unitario": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/movimentacoes/nova"
