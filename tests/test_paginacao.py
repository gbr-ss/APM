from datetime import datetime

from app.models.armario import Armario
from app.models.categoria import Categoria
from app.models.movimentacao import Movimentacao, Tipo_de_movimentacao
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.models.venda import Venda


def _tem_conteudo(response, texto):
    return texto in response.text


def test_usuarios_busca_ordenacao_e_paginas(cliente, db_session_test):
    db_session_test.add_all(
        [
            Usuario(
                nome=f"Usuario {numero:02}",
                email=f"usuario{numero:02}@teste.com",
                senha_hash="hash-de-teste",
                role="operador",
            )
            for numero in range(12)
        ]
    )
    db_session_test.commit()

    primeira_pagina = cliente.get("/usuarios/", params={"page": 1})
    segunda_pagina = cliente.get("/usuarios/", params={"page": 2})
    busca = cliente.get("/usuarios/", params={"busca": "Usuario 11"})
    pagina_negativa = cliente.get("/usuarios/", params={"page": -4})
    pagina_acima_do_total = cliente.get("/usuarios/", params={"page": 99})

    assert _tem_conteudo(primeira_pagina, "Usuario 00")
    assert _tem_conteudo(primeira_pagina, "Usuario 09")
    assert not _tem_conteudo(primeira_pagina, "Usuario 10")
    assert _tem_conteudo(segunda_pagina, "Usuario 10")
    assert _tem_conteudo(segunda_pagina, "Usuario 11")
    assert not _tem_conteudo(segunda_pagina, "Usuario 00")
    assert _tem_conteudo(busca, "Usuario 11")
    assert not _tem_conteudo(busca, "Usuario 01")
    assert _tem_conteudo(pagina_negativa, "Usuario 00")
    assert _tem_conteudo(pagina_acima_do_total, "Usuario 11")
    assert not _tem_conteudo(pagina_acima_do_total, "Usuario 00")


def test_produtos_filtram_por_busca_categoria_e_paginam(cliente, db_session_test):
    categoria = Categoria(nome="Bebidas")
    outra_categoria = Categoria(nome="Lanches")
    db_session_test.add_all([categoria, outra_categoria])
    db_session_test.flush()
    db_session_test.add_all(
        [
            Produto(
                nome=f"Bebida {numero:02}",
                preco=2.5,
                estoque_atual=10,
                categoria_id=categoria.id,
            )
            for numero in range(12)
        ]
        + [
            Produto(
                nome="Biscoito",
                preco=3,
                estoque_atual=4,
                categoria_id=outra_categoria.id,
            )
        ]
    )
    db_session_test.commit()

    primeira = cliente.get("/produtos/", params={"page": 1})
    segunda = cliente.get("/produtos/", params={"page": 2})
    filtrada = cliente.get(
        "/produtos/",
        params={"busca": "Bebida 11", "categoria_id": categoria.id},
    )

    assert _tem_conteudo(primeira, "Bebida 00")
    assert not _tem_conteudo(primeira, "Bebida 10")
    assert _tem_conteudo(segunda, "Bebida 10")
    assert _tem_conteudo(segunda, "Bebida 11")
    assert _tem_conteudo(filtrada, "Bebida 11")
    assert not _tem_conteudo(filtrada, "Biscoito")


def test_categorias_busca_ordenacao_e_paginacao(cliente, db_session_test):
    db_session_test.add_all([Categoria(nome=f"Categoria {numero:02}") for numero in range(12)])
    db_session_test.commit()

    primeira = cliente.get("/categorias/", params={"page": 1})
    segunda = cliente.get("/categorias/", params={"page": 2})
    busca = cliente.get("/categorias/", params={"busca": "Categoria 11"})

    assert _tem_conteudo(primeira, "Categoria 00")
    assert not _tem_conteudo(primeira, "Categoria 10")
    assert _tem_conteudo(segunda, "Categoria 10")
    assert _tem_conteudo(segunda, "Categoria 11")
    assert _tem_conteudo(busca, "Categoria 11")
    assert not _tem_conteudo(busca, "Categoria 01")


def test_movimentacoes_filtram_por_tipo_produto_e_paginam(cliente, db_session_test):
    produto = Produto(nome="Produto filtrado", preco=5, estoque_atual=20)
    outro = Produto(nome="Outro produto", preco=4, estoque_atual=20)
    db_session_test.add_all([produto, outro])
    db_session_test.flush()
    db_session_test.add_all(
        [
            Movimentacao(
                tipo=Tipo_de_movimentacao.ENTRADA,
                quantidade=numero + 1,
                preco_unitario=5,
                observacao=f"entrada-{numero:02}",
                produto_id=produto.id,
                usuario_id=1,
            )
            for numero in range(11)
        ]
        + [
            Movimentacao(
                tipo=Tipo_de_movimentacao.SAIDA,
                quantidade=1,
                preco_unitario=4,
                produto_id=outro.id,
                usuario_id=1,
            )
        ]
    )
    # A FK de usuÃ¡rio mantÃ©m a movimentaÃ§Ã£o ligada a um registro existente.
    db_session_test.add(
        Usuario(
            id=1,
            nome="Operador",
            email="operador-mov@teste.com",
            senha_hash="hash-de-teste",
            role="operador",
        )
    )
    db_session_test.commit()

    primeira = cliente.get("/movimentacoes/", params={"produto_id": produto.id, "tipo": "entrada"})
    segunda = cliente.get(
        "/movimentacoes/",
        params={"produto_id": produto.id, "tipo": "entrada", "page": 2},
    )
    sem_resultados = cliente.get(
        "/movimentacoes/",
        params={"produto_id": produto.id, "tipo": "saida"},
    )

    assert primeira.status_code == segunda.status_code == sem_resultados.status_code == 200
    # As linhas da tabela representam movimentaÃ§Ãµes; a paginaÃ§Ã£o informa a pÃ¡gina atual.
    assert 'aria-current="page">1<' in primeira.text
    assert 'aria-current="page">2<' in segunda.text
    assert "entrada-00" in primeira.text
    assert "entrada-10" not in primeira.text
    assert "entrada-10" in segunda.text
    assert "entrada-00" not in segunda.text
    assert "entrada-" not in sem_resultados.text


def test_armarios_filtram_status_busca_e_paginam(cliente, db_session_test):
    armarios = [
        Armario(
            numero=f"A-{numero:02}",
            descricao="Bloco A",
            status="disponivel" if numero < 11 else "bloqueado",
        )
        for numero in range(12)
    ]
    db_session_test.add_all(armarios)
    db_session_test.commit()

    primeira = cliente.get("/armarios/", params={"status": "disponivel", "page": 1})
    segunda = cliente.get("/armarios/", params={"status": "disponivel", "page": 2})
    busca = cliente.get("/armarios/", params={"busca": "A-11"})

    assert _tem_conteudo(primeira, "A-00")
    assert not _tem_conteudo(primeira, "A-10")
    assert _tem_conteudo(segunda, "A-10")
    assert not _tem_conteudo(segunda, "A-11")
    assert _tem_conteudo(busca, "A-11")


def test_historico_de_vendas_pagina_e_limita_pagina_invalida(cliente, db_session_test):
    db_session_test.add_all(
        [
            Venda(
                total_bruto=float(numero),
                total_liquido=float(numero),
                criado_em=datetime(2026, 1, 1, 12, numero),
            )
            for numero in range(1, 13)
        ]
    )
    db_session_test.commit()

    primeira = cliente.get("/pdv/historico", params={"page": 1})
    segunda = cliente.get("/pdv/historico", params={"page": 2})
    fora_da_faixa = cliente.get("/pdv/historico", params={"page": 999})

    assert primeira.status_code == segunda.status_code == fora_da_faixa.status_code == 200
    assert "#12" in primeira.text
    assert "#2" not in primeira.text
    assert "#2" in segunda.text
    assert "#12" not in segunda.text
    assert "#2" in fora_da_faixa.text


