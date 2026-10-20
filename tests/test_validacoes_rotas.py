def test_rotas_de_edicao_inexistentes_redirecionam(cliente):
    rotas = [
        "/usuarios/999/editar",
        "/clientes/999/editar",
        "/categorias/999/editar",
        "/produtos/999/editar",
        "/movimentacoes/produto/999",
        "/armarios/999/editar",
    ]
    for caminho in rotas:
        response = cliente.get(caminho, follow_redirects=False)
        assert response.status_code == 302, f"{caminho}: {response.status_code}"
