import psycopg2
from flask import Flask, redirect, render_template_string, url_for

app = Flask(__name__)

# Votre chaîne de connexion PostgreSQL Aiven
DATABASE_URL = "postgres://avnadmin:VOTRE_MOT_DE_PASSE@pg-368b4833-bastianbary17-5fbd.e.aivencloud.com:18969/defaultdb?sslmode=require"


def verifier_et_creer_table():
    """S'assure que la table de contrôle existe dans la base."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS controle_script (
                id INT PRIMARY KEY,
                statut VARCHAR(20) DEFAULT 'RUNNING'
            );
        """
        )
        cur.execute(
            """
            INSERT INTO controle_script (id, statut) VALUES (1, 'RUNNING')
            ON CONFLICT (id) DO NOTHING;
        """
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur d'initialisation de la table : {e}")


def obtenir_statut():
    """Lit le statut actuel dans la base de données."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT statut FROM controle_script WHERE id = 1;")
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res[0] if res else "UNKNOWN"
    except Exception as e:
        print(f"Erreur de lecture du statut : {e}")
        return "ERROR"


def modifier_statut(nouveau_statut):
    """Met à jour le statut ('RUNNING' ou 'STOP') dans la base."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "UPDATE controle_script SET statut = %s WHERE id = 1;",
            (nouveau_statut,),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur de modification du statut : {e}")


# Page HTML intégrée directement dans le code
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contrôle du Script de Capture</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f4f4f9; }
        .card { background: white; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .status { font-weight: bold; font-size: 1.2em; padding: 5px 10px; border-radius: 4px; }
        .running { color: green; background-color: #e6ffe6; }
        .stop { color: red; background-color: #ffe6e6; }
        button { padding: 12px 24px; font-size: 1em; border: none; border-radius: 6px; cursor: pointer; margin: 10px; }
        .btn-stop { background-color: #ff4d4d; color: white; }
        .btn-start { background-color: #4caf50; color: white; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Panneau de Contrôle</h1>
        <p>Statut actuel du script : 
            <span class="status {{ 'running' if statut == 'RUNNING' else 'stop' }}">{{ statut }}</span>
        </p>
        
        <form action="/toggle" method="POST">
            {% if statut == 'RUNNING' %}
                <button type="submit" class="btn-stop">🔴 Arrêter le script</button>
            {% else %}
                <button type="submit" class="btn-start">🟢 Relancer le script</button>
            {% endif %}
        </form>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    statut = obtenir_statut()
    return render_template_string(HTML_TEMPLATE, statut=statut)


@app.route("/toggle", methods=["POST"])
def toggle():
    statut_actuel = obtenir_statut()
    nouveau_statut = "STOP" if statut_actuel == "RUNNING" else "RUNNING"
    modifier_statut(nouveau_statut)
    return redirect(url_for("index"))


if __name__ == "__main__":
    verifier_et_creer_table()
    app.run(host="0.0.0.0", port=5000, debug=True)