"""
Modulo de autenticacao federada com o ApexAmostra.

Quando APEX_AMOSTRA_URL estiver configurado, o login do ServidorApex
tambem aceita as credenciais do ApexAmostra como fallback.

Perfis do ApexAmostra mapeados:
  "Administrador" -> is_admin=True
  Qualquer outro  -> is_admin=False
"""
import logging

logger = logging.getLogger(__name__)


def autenticar_apex(apex_url: str, username: str, password: str):
    """
    Tenta autenticar via API do ApexAmostra.

    Retorna dict com {nome, is_admin} em caso de sucesso, ou None em caso de falha.
    """
    if not apex_url:
        return None

    try:
        import urllib.request
        import urllib.error
        import json

        payload = json.dumps({"user": username, "pass": password}).encode("utf-8")
        url = apex_url.rstrip("/") + "/api/login"

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("success"):
            return None

        user_data = data.get("user", {})
        perfil = user_data.get("perfil", "")
        nome = user_data.get("nome", username)
        is_admin = perfil == "Administrador"

        return {"nome": nome, "is_admin": is_admin}

    except Exception as exc:
        logger.warning("Falha ao contatar ApexAmostra (%s): %s", apex_url, exc)
        return None


def obter_ou_criar_shadow_user(db, User, username: str, nome: str, is_admin: bool):
    """
    Cria (ou atualiza) um usuario local 'espelho' para o usuario do ApexAmostra.
    A senha de shadow e inutilizavel — login so funciona via ApexAmostra.
    """
    import secrets
    from werkzeug.security import generate_password_hash

    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(
            username=username,
            nome=nome,
            is_admin=is_admin,
            ativo=True,
        )
        # Senha aleatoria inutilizavel (so autentica via ApexAmostra)
        user.password_hash = generate_password_hash(secrets.token_hex(32))
        db.session.add(user)
    else:
        # Atualiza perfil em caso de mudanca no ApexAmostra
        user.nome = nome
        user.is_admin = is_admin
        user.ativo = True

    db.session.commit()
    return user
