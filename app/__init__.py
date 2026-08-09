import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "warning"
    csrf.init_app(app)

    from . import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    from .auth import auth_bp
    from .notas import notas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(notas_bp)

    register_cli(app)

    @app.context_processor
    def inject_globals():
        return {"categorias": app.config["CATEGORIAS"]}

    return app


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Cria as tabelas do banco de dados."""
        with app.app_context():
            db.create_all()
        click.echo("Banco de dados inicializado.")

    @app.cli.command("criar-admin")
    @click.option("--username", prompt=True)
    @click.option("--nome", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def criar_admin(username, nome, password):
        """Cria (ou promove) um usuario administrador."""
        from .models import User

        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if user is None:
                user = User(username=username, nome=nome, is_admin=True)
                user.set_password(password)
                db.session.add(user)
            else:
                user.nome = nome
                user.is_admin = True
                user.set_password(password)
            db.session.commit()
        click.echo(f"Administrador '{username}' pronto.")
