from flask import Flask

from routes.dashboard_routes import dashboard_bp
from routes.public_routes import public_bp
from routes.whatsapp_routes import whatsapp_bp

app = Flask(__name__)

app.register_blueprint(public_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(whatsapp_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)
