from app.auth import hash_senha
from app.models.usuario import Usuario


def test_criar_editar_e_desativar_usuario(cliente, db_session_test):
    criado = cliente.post(
        "/usuarios/novo",
        data={"nome": "Operador Um", "email": "operador@teste.com", "senha": "senha123", "role": "operador"},
        follow_redirects=False,
    )
    assert criado.status_code == 302
    usuario = db_session_test.query(Usuario).filter_by(email="operador@teste.com").one()
    assert usuario.senha_hash != "senha123"

    formulario = cliente.get(f"/usuarios/{usuario.id}/editar")
    assert formulario.status_code == 200
    editado = cliente.post(
        f"/usuarios/{usuario.id}/editar",
        data={"nome": "Operador Editado", "email": usuario.email, "role": "admin", "senha": ""},
        follow_redirects=False,
    )
    assert editado.status_code == 302
    assert usuario.nome == "Operador Editado"
    assert usuario.role == "admin"

    desativado = cliente.post(f"/usuarios/{usuario.id}/toggle-ativo", follow_redirects=False)
    assert desativado.status_code == 302
    assert usuario.ativo is False

    ativado = cliente.post(f"/usuarios/{usuario.id}/toggle-ativo", follow_redirects=False)
    assert ativado.status_code == 302
    assert usuario.ativo is True


def test_usuario_rejeita_email_duplicado_perfil_invalido_e_autodesativacao(
    cliente, db_session_test
):
    admin = Usuario(
        nome="Admin de teste",
        email="teste@aapm.com",
        senha_hash=hash_senha("senha123"),
        role="admin",
        ativo=True,
    )
    db_session_test.add(admin)
    db_session_test.commit()

    duplicado = cliente.post(
        "/usuarios/novo",
        data={"nome": "Outro", "email": admin.email, "senha": "senha123", "role": "operador"},
    )
    perfil_invalido = cliente.post(
        "/usuarios/novo",
        data={"nome": "Outro", "email": "outro@teste.com", "senha": "senha123", "role": "root"},
    )
    proprio = cliente.post(f"/usuarios/{admin.id}/toggle-ativo", follow_redirects=False)

    assert duplicado.status_code == 400
    assert perfil_invalido.status_code == 400
    assert proprio.headers["location"].endswith("erro=autoproprio")
    assert admin.ativo is True


def test_edicao_de_usuario_rejeita_email_duplicado_e_perfil_invalido(
    cliente, db_session_test
):
    usuarios = [
        Usuario(
            nome=f"Operador {letra}",
            email=f"operador-{letra.lower()}@teste.com",
            senha_hash=hash_senha("senha123"),
            role="operador",
        )
        for letra in ("A", "B")
    ]
    db_session_test.add_all(usuarios)
    db_session_test.commit()
    alvo, outro = usuarios

    email_duplicado = cliente.post(
        f"/usuarios/{alvo.id}/editar",
        data={"nome": alvo.nome, "email": outro.email, "role": "operador"},
    )
    perfil_invalido = cliente.post(
        f"/usuarios/{alvo.id}/editar",
        data={"nome": alvo.nome, "email": alvo.email, "role": "root"},
    )

    assert email_duplicado.status_code == 400
    assert perfil_invalido.status_code == 400
    assert alvo.email == "operador-a@teste.com"
    assert alvo.role == "operador"
