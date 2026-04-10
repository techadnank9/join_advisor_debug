import traceback
import os

from flask import Flask, jsonify, render_template, request

from main import DEFAULT_DB_PATH, DEFAULT_MODEL, DEFAULT_TABLE_A, DEFAULT_TABLE_B, run_join_analysis


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["TRUSTED_HOSTS"] = ["127.0.0.1", "localhost", "[::1]"]

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            default_db_path=DEFAULT_DB_PATH,
            default_table_a=DEFAULT_TABLE_A,
            default_table_b=DEFAULT_TABLE_B,
            default_model=DEFAULT_MODEL,
        )

    @app.post("/analyze")
    def analyze():
        payload = request.get_json(silent=True) or request.form
        db_path = (payload.get("db_path") or DEFAULT_DB_PATH).strip()
        table_a = (payload.get("table_a") or DEFAULT_TABLE_A).strip()
        table_b = (payload.get("table_b") or DEFAULT_TABLE_B).strip()
        model = (payload.get("model") or DEFAULT_MODEL).strip()

        try:
            result = run_join_analysis(db_path, table_a, table_b, model)
            return jsonify({"ok": True, **result})
        except Exception as exc:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                ),
                500,
            )

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    create_app().run(debug=False, host="0.0.0.0", port=port)
