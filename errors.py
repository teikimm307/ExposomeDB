from flask import render_template, Flask


def configure_app(app: Flask):
    @app.errorhandler(404)
    def handler_404(msg):
        return render_template("errors/404.html")

    @app.errorhandler(403)
    def handler_403(msg):
        return render_template("errors/403.html")
