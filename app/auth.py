from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from . import db
from .models import User

auth_bp = Blueprint("auth", __name__)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Apenas administradores podem acessar essa página.", "danger")
            return redirect(url_for("notas.dashboard"))
        return f(*args, **kwargs)

    return wrapper


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("notas.dashboard"))

    if request.method == "POST":
        from flask import current_app
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # 1. Tenta autenticacao local
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.ativo:
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("notas.dashboard"))

        # 2. Fallback: tenta ApexAmostra (se URL configurada)
        apex_url = current_app.config.get("APEX_AMOSTRA_URL", "")
        if apex_url:
            from .apex_auth import autenticar_apex, obter_ou_criar_shadow_user
            resultado = autenticar_apex(apex_url, username, password)
            if resultado:
                shadow = obter_ou_criar_shadow_user(
                    db, User,
                    username=username,
                    nome=resultado["nome"],
                    is_admin=resultado["is_admin"],
                )
                login_user(shadow, remember=True)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("notas.dashboard"))

        flash("Usuário ou senha inválidos.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/usuarios")
@login_required
@admin_required
def usuarios():
    todos = User.query.order_by(User.nome).all()
    return render_template("usuarios.html", usuarios=todos)


@auth_bp.route("/usuarios/novo", methods=["POST"])
@login_required
@admin_required
def novo_usuario():
    username = request.form.get("username", "").strip()
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    is_admin = bool(request.form.get("is_admin"))

    if not username or not nome or not password:
        flash("Preencha todos os campos obrigatórios.", "danger")
        return redirect(url_for("auth.usuarios"))

    if User.query.filter_by(username=username).first():
        flash("Já existe um usuário com esse login.", "danger")
        return redirect(url_for("auth.usuarios"))

    user = User(username=username, nome=nome, email=email, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)

    db.session.commit()
    flash(f"Usuário '{nome}' criado com sucesso.", "success")
    return redirect(url_for("auth.usuarios"))


@auth_bp.route("/usuarios/<int:user_id>/alternar", methods=["POST"])
@login_required
@admin_required
def alternar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Você não pode desativar seu próprio usuário.", "warning")
        return redirect(url_for("auth.usuarios"))
    user.ativo = not user.ativo
    db.session.commit()
    estado = "ativado" if user.ativo else "desativado"
    flash(f"Usuário '{user.nome}' {estado}.", "info")
    return redirect(url_for("auth.usuarios"))
