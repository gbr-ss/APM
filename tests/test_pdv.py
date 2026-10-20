import json

import pytest

from app.models.cliente import Cliente
from app.models.produto import Produto
from app.models.venda import ItemVenda, PagamentoVenda, Venda


def criar_produto(db_session_test, *, nome="Produto de teste", preco=30.0, estoque=10):
    produto = Produto(
        nome=nome,
        preco=preco,
        estoque_atual=estoque,
        ativo=True,
    )
    db_session_test.add(produto)
    db_session_test.commit()
    db_session_test.refresh(produto)
    return produto


def finalizar(
    cliente,
    produto,
    pagamentos,
    *,
    quantidade=1,
    cliente_id=0,
    desconto_tipo="nenhum",
    desconto_valor=0,
    follow_redirects=False,
):
    return cliente.post(
        "/pdv/finalizar",
        data={
            "carrinho_json": json.dumps([
                {"produto_id": produto.id, "quantidade": quantidade}
            ]),
            "cliente_id": cliente_id,
            "pagamentos_json": json.dumps(pagamentos),
            "desconto_manual_tipo": desconto_tipo,
            "desconto_manual_valor": desconto_valor,
        },
        follow_redirects=follow_redirects,
    )


def test_tela_pdv_e_historico_retorna_200(cliente):
    assert cliente.get("/pdv/").status_code == 200
    assert cliente.get("/pdv/historico").status_code == 200


def test_finalizar_venda_com_um_pagamento_persiste_e_atualiza_estoque(
    cliente, db_session_test
):
    produto = criar_produto(db_session_test, preco=30, estoque=4)

    response = finalizar(cliente, produto, [{"metodo": "pix", "valor": 30}])

    assert response.status_code == 302
    assert response.headers["location"].startswith("/pdv/venda/")
    venda = db_session_test.query(Venda).one()
    pagamento = db_session_test.query(PagamentoVenda).one()
    item = db_session_test.query(ItemVenda).one()
    db_session_test.refresh(produto)
    assert venda.total_bruto == 30
    assert venda.total_liquido == 30
    assert (pagamento.metodo, pagamento.valor) == ("pix", 30)
    assert item.quantidade == 1
    assert produto.estoque_atual == 3


def test_finalizar_venda_com_quatro_pagamentos_e_desconto_mostra_no_historico(
    cliente, db_session_test
):
    produto = criar_produto(db_session_test, preco=40)
    pagamentos = [
        {"metodo": "pix", "valor": 5},
        {"metodo": "debito", "valor": 5},
        {"metodo": "credito", "valor": 10},
        {"metodo": "dinheiro", "valor": 10},
    ]

    response = finalizar(
        cliente,
        produto,
        pagamentos,
        desconto_tipo="valor",
        desconto_valor=10,
    )

    assert response.status_code == 302
    venda = db_session_test.query(Venda).one()
    assert venda.total_bruto == 40
    assert venda.total_liquido == 30
    assert venda.desconto_manual_tipo == "valor"
    assert venda.desconto_manual_valor == 10
    assert db_session_test.query(PagamentoVenda).count() == 4

    comprovante = cliente.get(f"/pdv/venda/{venda.id}")
    historico = cliente.get("/pdv/historico")
    assert comprovante.status_code == 200
    assert "Pagamento 2" in comprovante.text
    assert "Pagamento 4" in comprovante.text
    assert "dinheiro" in comprovante.text.lower()
    assert historico.status_code == 200
    assert "dinheiro" in historico.text.lower()
    assert "R$ 30.00" in historico.text


def test_desconto_percentual_de_associado_e_manual_sao_aplicados(
    cliente, db_session_test
):
    produto = criar_produto(db_session_test, preco=100)
    associado = Cliente(nome="Associado teste", is_associado=True, ativo=True)
    db_session_test.add(associado)
    db_session_test.commit()

    response = finalizar(
        cliente,
        produto,
        [{"metodo": "dinheiro", "valor": 85}],
        cliente_id=associado.id,
        desconto_tipo="percentual",
        desconto_valor=5,
    )

    assert response.status_code == 302
    venda = db_session_test.query(Venda).one()
    assert venda.desconto_percentual == 10
    assert venda.desconto_manual_tipo == "percentual"
    assert venda.desconto_manual_valor == 5
    assert venda.total_liquido == 85
    assert venda.desconto_valor == 15


@pytest.mark.parametrize(
    "pagamentos",
    [
        [{"metodo": "pix", "valor": 29.99}],
        [{"metodo": "metodo-inexistente", "valor": 30}],
        [{"metodo": "pix", "valor": 30}, {"metodo": "debito", "valor": 1}],
        [{"metodo": "pix", "valor": 0}],
        [],
    ],
)
def test_pagamento_invalido_nao_cria_venda(cliente, db_session_test, pagamentos):
    produto = criar_produto(db_session_test)

    response = finalizar(cliente, produto, pagamentos)

    assert response.status_code == 302
    assert response.headers["location"] == "/pdv?erro=pagamento"
    assert db_session_test.query(Venda).count() == 0
    db_session_test.refresh(produto)
    assert produto.estoque_atual == 10


@pytest.mark.parametrize(
    ("tipo", "valor"),
    [
        ("valor", 31),
        ("percentual", 101),
        ("valor", -1),
    ],
)
def test_desconto_acima_do_limite_nao_cria_venda(
    cliente, db_session_test, tipo, valor
):
    produto = criar_produto(db_session_test)

    response = finalizar(
        cliente,
        produto,
        [{"metodo": "pix", "valor": 30}],
        desconto_tipo=tipo,
        desconto_valor=valor,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/pdv?erro=desconto"
    assert db_session_test.query(Venda).count() == 0


def test_desconto_de_associado_nao_pode_ser_excedido(cliente, db_session_test):
    produto = criar_produto(db_session_test, preco=100)
    associado = Cliente(nome="Associado teste", is_associado=True, ativo=True)
    db_session_test.add(associado)
    db_session_test.commit()

    response = finalizar(
        cliente,
        produto,
        [{"metodo": "pix", "valor": 10}],
        cliente_id=associado.id,
        desconto_tipo="valor",
        desconto_valor=91,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/pdv?erro=desconto"
    assert db_session_test.query(Venda).count() == 0


def test_quantidade_invalida_ou_estoque_insuficiente_nao_cria_venda(
    cliente, db_session_test
):
    produto = criar_produto(db_session_test, estoque=2)
    pagamento = [{"metodo": "pix", "valor": 30}]

    response_quantidade = finalizar(cliente, produto, pagamento, quantidade=0)
    response_estoque = finalizar(cliente, produto, pagamento, quantidade=3)

    assert response_quantidade.headers["location"] == "/pdv?erro=quantidade"
    assert response_estoque.headers["location"] == "/pdv?erro=estoque"
    assert db_session_test.query(Venda).count() == 0
    db_session_test.refresh(produto)
    assert produto.estoque_atual == 2


def test_carrinho_malformado_vazio_e_venda_inexistente_sao_tratados(cliente):
    malformado = cliente.post(
        "/pdv/finalizar",
        data={"carrinho_json": "{"},
        follow_redirects=False,
    )
    vazio = cliente.post(
        "/pdv/finalizar",
        data={"carrinho_json": "[]"},
        follow_redirects=False,
    )

    assert malformado.headers["location"] == "/pdv?erro=json"
    assert vazio.headers["location"] == "/pdv?erro=vazio"
    assert cliente.get("/pdv/venda/99999", follow_redirects=False).status_code == 302
