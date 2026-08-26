"""Flask 应用入口

负责创建应用实例、注册蓝图、提供首页路由,并启动服务。
"""
import os
from typing import Any

from flask import Flask, render_template, send_from_directory

from config import get_config
from api.controllers.mbti_controller import mbti_bp

# 项目根目录
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))


def create_app(env: str = "default") -> Flask:
    """创建并配置 Flask 应用实例

    Args:
        env: 环境名称,可选 development / production / default

    Returns:
        配置完成的 Flask 应用实例
    """
    config = get_config(env)
    app: Flask = Flask(
        __name__,
        static_folder=config.STATIC_FOLDER,
        template_folder=config.TEMPLATE_FOLDER,
    )
    app.config.from_object(config)

    # 注册 API 蓝图
    app.register_blueprint(mbti_bp)

    # 首页路由:返回单页应用
    @app.route("/")
    def index() -> Any:
        """应用首页"""
        return render_template("index.html")

    # 兜底路由:非 API 请求统一返回首页(支持前端路由)
    @app.route("/<path:path>")
    def fallback(path: str) -> Any:
        """兜底路由,优先返回静态文件,否则返回首页"""
        full_path: str = os.path.join(BASE_DIR, config.STATIC_FOLDER, path)
        if os.path.isfile(full_path):
            return send_from_directory(
                os.path.join(BASE_DIR, config.STATIC_FOLDER), path)
        # 非静态文件的路径(如前端路由)统一返回首页
        return render_template("index.html")

    return app


# 全局应用实例(供 flask run 与命令行直接运行使用)
app: Flask = create_app(os.getenv("FLASK_ENV", "default"))


if __name__ == "__main__":
    # 开发模式下以调试模式启动
    app.run(host="0.0.0.0", port=5000, debug=True)
