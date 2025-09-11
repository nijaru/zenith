"""Flask benchmark application."""

from datetime import datetime
from functools import wraps

import jwt
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from pydantic import BaseModel, ValidationError

# Models
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)


class UserModel(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


class CreateUserModel(BaseModel):
    name: str
    email: str


# App
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


# Auth decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token, "benchmark-secret-key-123", algorithms=["HS256"]
            )
            request.current_user = payload
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated_function


# Initialize database
with app.app_context():
    db.create_all()
    # Seed data
    for i in range(100):
        user = User(
            name=f"User {i}", email=f"user{i}@example.com", created_at=datetime.now()
        )
        db.session.add(user)
    db.session.commit()


# Routes
@app.route("/")
def hello_world():
    return jsonify({"message": "Hello, World!"})


@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }
    )


@app.route("/users")
def list_users():
    limit = request.args.get("limit", 100, type=int)
    users = User.query.limit(limit).all()

    return jsonify(
        [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ]
    )


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    # Validate with Pydantic
    try:
        validated = CreateUserModel(**data)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user = User(name=validated.name, email=validated.email, created_at=datetime.now())
    db.session.add(user)
    db.session.commit()

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }
    )


@app.route("/protected")
@require_auth
def protected_route():
    return jsonify({"user": request.current_user})


@app.route("/validate", methods=["POST"])
def validate_data():
    data = request.get_json()

    try:
        validated = CreateUserModel(**data)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    return jsonify({"validated": True, "data": validated.model_dump()})


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    content = file.read()
    return jsonify({"size": len(content), "message": "File processed"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8002, debug=False)
