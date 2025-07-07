from flask import Flask
from auth.routes import auth_bp
from database import init_db

app = Flask(__name__)
init_db(app)
app.register_blueprint(auth_bp)


if __name__ == "__main__":
    app.run(debug=True)
