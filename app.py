from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    # простой healthcheck, который будет использоваться потом в Docker и CD
    return jsonify({"status": "ok"}), 200


@app.route("/")
def index():
    return "Hello from CD demo v2!", 200


if __name__ == "__main__":
    # debug выключим — сразу “как в проде”, без autoreload
    app.run(host="0.0.0.0", port=8000)
