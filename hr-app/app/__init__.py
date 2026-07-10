import os
from flask import Flask
from flask_login import LoginManager
from app.models import db, Employee

def create_app(test_config=None):
    # 修改 template 和 static 轉向 app 目錄下
    app = Flask(__name__, instance_relative_config=True, template_folder='templates', static_folder='static')
    
    # 預設配置
    app.config.from_mapping(
        SECRET_KEY='dev-secret-key-change-in-production',
        SQLALCHEMY_DATABASE_URI='sqlite:///hr_app.sqlite',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # 確保 instance 目錄存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Employee.query.get(int(user_id))

    # 註冊 Blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # 自動建立資料表 (如果是 MySQL 且資料庫已存在)
    with app.app_context():
        db.create_all()

    return app
