from app.auth import hash_senha
from app.auth import verificar_senha
from app.models.usuario import Usuario


def test_hash_senha_nao_retorna_senha_em_texto():
    senha = "senha-de-teste-123"
    assert hash_senha(senha) != senha


def test_verificar_senha_aceita_senha_correta():
    senha = "senha-de-teste-123"
    assert verificar_senha(senha, hash_senha(senha)) is True


def test_verificar_senha_rejeita_senha_incorreta():
    senha_hash = hash_senha("senha-correta")
    assert verificar_senha("senha-errada", senha_hash) is False


def test_login_valido_define_cookie_e_redireciona(
    cliente, db_session_test, monkeypatch
):
    import app.auth as auth

    monkeypatch.setattr(auth, "SECRET_KEY", "chave-secreta-de-teste")
    monkeypatch.setattr(auth, "ALGORITHM", "HS256")
    monkeypatch.setattr(auth, "ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    db_session_test.add(
        Usuario(
            nome="Gabriel Teste",
            email="gabriel@teste.com",
            senha_hash=hash_senha("senha-correta"),
            role="admin",
            ativo=True,
        )
    )
    db_session_test.commit()

    response = cliente.post(
        "/auth/login",
        data={"email": "gabriel@teste.com", "senha": "senha-correta"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert "access_token" in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


def test_login_rejeita_senha_incorreta_e_usuario_inativo(cliente, db_session_test):
    db_session_test.add_all(
        [
            Usuario(
                nome="Ativo",
                email="ativo@teste.com",
                senha_hash=hash_senha("senha-correta"),
                role="operador",
                ativo=True,
            ),
            Usuario(
                nome="Inativo",
                email="inativo@teste.com",
                senha_hash=hash_senha("senha-correta"),
                role="operador",
                ativo=False,
            ),
        ]
    )
    db_session_test.commit()

    senha_incorreta = cliente.post(
        "/auth/login",
        data={"email": "ativo@teste.com", "senha": "errada"},
    )
    email_inexistente = cliente.post(
        "/auth/login",
        data={"email": "nao-existe@teste.com", "senha": "errada"},
    )
    inativo = cliente.post(
        "/auth/login",
        data={"email": "inativo@teste.com", "senha": "senha-correta"},
    )

    assert senha_incorreta.status_code == email_inexistente.status_code == 401
    assert inativo.status_code == 403


def test_rotas_protegidas_rejeitam_requisicao_sem_login(cliente_sem_autenticacao):
    assert cliente_sem_autenticacao.get("/usuarios/").status_code == 401
    assert cliente_sem_autenticacao.get("/pdv/").status_code == 401


def test_logout_redireciona_e_remove_cookie(cliente):
    response = cliente.get("/auth/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/auth/login"
    assert "access_token" in response.headers.get("set-cookie", "")
