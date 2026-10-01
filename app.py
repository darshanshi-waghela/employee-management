import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required
)
from werkzeug.security import generate_password_hash, check_password_hash
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import CollectorRegistry

db = SQLAlchemy()
login_manager = LoginManager()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "position": self.position,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Login required"}), 401


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///employees.db"
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    PrometheusMetrics(app, registry=CollectorRegistry())

    with app.app_context():
        db.create_all()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "username already exists"}), 409
        user = User(
            username=username, password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "registered"}), 201

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        user = User.query.filter_by(username=data.get("username")).first()
        if user and check_password_hash(user.password_hash, data.get("password", "")):
            login_user(user)
            return jsonify({"message": "logged in"}), 200
        return jsonify({"error": "invalid credentials"}), 401

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        return jsonify({"message": "logged out"}), 200

    @app.get("/employees")
    @login_required
    def list_employees():
        return jsonify([e.to_dict() for e in Employee.query.all()]), 200

    @app.post("/employees")
    @login_required
    def create_employee():
        data = request.get_json(silent=True) or {}
        if not data.get("name") or not data.get("email"):
            return jsonify({"error": "name and email required"}), 400
        if Employee.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "email already exists"}), 409
        emp = Employee(
            name=data["name"],
            email=data["email"],
            department=data.get("department"),
            position=data.get("position"),
        )
        db.session.add(emp)
        db.session.commit()
        return jsonify(emp.to_dict()), 201

    @app.get("/employees/<int:emp_id>")
    @login_required
    def get_employee(emp_id):
        return jsonify(db.get_or_404(Employee, emp_id).to_dict()), 200

    @app.put("/employees/<int:emp_id>")
    @login_required
    def update_employee(emp_id):
        emp = db.get_or_404(Employee, emp_id)
        data = request.get_json(silent=True) or {}
        for field in ("name", "email", "department", "position"):
            if field in data:
                setattr(emp, field, data[field])
        db.session.commit()
        return jsonify(emp.to_dict()), 200

    @app.delete("/employees/<int:emp_id>")
    @login_required
    def delete_employee(emp_id):
        emp = db.get_or_404(Employee, emp_id)
        db.session.delete(emp)
        db.session.commit()
        return jsonify({"message": "deleted"}), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)