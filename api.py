import logging

from functools import wraps
from flask import Flask, jsonify, request

from logging_conf import configure_logging

configure_logging()
logger = logging.getLogger("app")
app = Flask(__name__)

users = [{"name": "Juan", "age": 30}, {"name": "Pedro", "age": 35}]


def validate_user_data(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if request.method in ['POST', 'PUT']:
                user_data = request.get_json()
                
                if not isinstance(user_data, dict):
                    return jsonify({"error": "Los datos deben ser un objeto JSON"}), 400

                if "name" not in user_data or not isinstance(user_data["name"], str):
                    return jsonify({"error": "El campo 'name' es requerido y debe ser string"}), 400

                if "age" not in user_data or not isinstance(user_data["age"], int):
                    return jsonify({"error": "El campo 'age' es requerido y debe ser entero"}), 400

            return func(*args, **kwargs)
            
        except Exception as exc:
            logger.error(f"Error en validación: {str(exc)}")
            return jsonify({"error": "Error en validación de datos"}), 400
    
    return wrapper


@app.route("/users", methods=["GET"])
def get_all_users():
    logger.info(f"get_all_users: {users}")
    return jsonify(users), 200


@app.route("/users/<string:name>", methods=["GET"])
def get_user_by_name(name):
    try:
        logger.info(f"get user: {name}")
        for user in users:
            if user.get("name") == name:
                return jsonify(user), 200

        return jsonify(f"No se encontró el usuario {name}"), 404

    except Exception as exc:
        logger.error(exc)
        return jsonify("Error de servidor"), 500


@app.route("/users", methods=["POST"])
@validate_user_data
def insert_user():
    try:
        user_data = request.json
        logger.info(f"insert user {user_data}")
        users.append(user_data)
        return jsonify(users), 201

    except Exception as exc:
        logger.error(exc)
        return jsonify("Error de servidor"), 500


@app.route("/users/<string:name>", methods=["PUT"])
@validate_user_data
def update_user(name):
    try:
        logger.info(f"update user {name}")
        user_data = request.json
        user_index = next((i for i, u in enumerate(users) if u["name"] == name), None)
        
        if user_index is None:
            return jsonify({"error": f"No se encontró el usuario {name}"}), 404
            
        users[user_index] = user_data
        return jsonify(users), 200

    except Exception as exc:
        logger.error(exc)
        return jsonify("Error de servidor"), 500


@app.route("/users/<string:name>", methods=["DELETE"])
def remove_user(name):
    try:
        logger.info(f"remove user {name}")
        global users
        users = [u for u in users if u["name"] != name]
        return jsonify(users), 200

    except Exception as exc:
        logger.error(exc)
        return jsonify("Error de servidor"), 500


if __name__ == "__main__":
    logger.info("API Ready!")
    app.run(debug=True)
