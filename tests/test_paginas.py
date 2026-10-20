import pytest


@pytest.mark.parametrize(
    "caminho",
    [
        pytest.param("/auth/login", id="login"),
        pytest.param("/", id="pagina-inicial"),
        pytest.param("/usuarios/", id="lista-usuarios"),
        pytest.param("/usuarios/novo", id="formulario-usuario"),
        pytest.param("/categorias/", id="lista-categorias"),
        pytest.param("/categorias/nova", id="formulario-categoria"),
        pytest.param("/produtos/", id="lista-produtos"),
        pytest.param("/produtos/novo", id="formulario-produto"),
        pytest.param("/clientes/", id="lista-clientes"),
        pytest.param("/clientes/novo", id="formulario-cliente"),
        pytest.param("/movimentacoes/", id="lista-movimentacoes"),
        pytest.param("/movimentacoes/nova", id="formulario-movimentacao"),
        pytest.param("/armarios/", id="lista-armarios"),
        pytest.param("/armarios/novo", id="formulario-armario"),
        pytest.param("/armarios/historico", id="historico-armarios"),
        pytest.param("/pdv/", id="tela-pdv"),
        pytest.param("/pdv/historico", id="historico-vendas"),
    ],
)
def test_pagina_carrega_com_sucesso(cliente, caminho):
    response = cliente.get(caminho)
    assert response.status_code == 200, f"{caminho}: {response.status_code}"


def test_pagina_inicial_exibe_dashboard(cliente):
    response = cliente.get("/")
    assert response.status_code == 200
    assert "dashboard" in response.text.lower()
