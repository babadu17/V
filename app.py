from datetime import datetime, timezone
import psycopg2
from flask import Flask, redirect, render_template_string, url_for

app = Flask(__name__)

DATABASE_URL = "postgres://avnadmin:AVNS__GlfxlePDxDk14ehlKA@pg-368b4833-bastianbary17-5fbd.e.aivencloud.com:18969/defaultdb?sslmode=require"

def obtenir_infos_etat():
    """Récupère le statut et calcule si le PC est en ligne (dernier signal < 15 min)."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # S'assure que la table existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controle_script (
                id INT PRIMARY KEY,
                statut VARCHAR(20) DEFAULT 'RUNNING',
                dernier_signal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("INSERT INTO controle_script (id, statut) VALUES (1, 'RUNNING') ON CONFLICT (id) DO NOTHING;")
        conn.commit()
        
        cur.execute("SELECT statut, dernier_signal FROM controle_script WHERE id = 1;")
        res = cur.fetchone()
        cur.close()
        conn.close()
        
        if not res:
            return "UNKNOWN", False
            
        statut = res[0]
        dernier_signal = res[1]
        
        # Vérifie si le PC a envoyé un signal il y a moins de 15 minutes (900 secondes)
        pc_en_ligne = False
        if dernier_signal:
            # Assure la compatibilité UTC
            if dernier_signal.tzinfo is None:
                dernier_signal = dernier_signal.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - dernier_signal
            if delta.total_seconds() < 900:
                pc_en_ligne = True
                
        return statut, pc_en_ligne
    except Exception as e:
        return f"ERROR: {e}", False

@app.route("/")
def index():
    statut, pc_en_ligne = obtenir_infos_etat()
    
    html_template = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panneau de Contrôle - Agent</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f4f4f9; }
            .card { background: white; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 350px; }
            .badge { font-weight: bold; padding: 6px 12px; border-radius: 6px; display: inline-block; margin-top: 5px; }
            .running { color: #155724; background-color: #d4edda; }
            .stop { color: #721c24; background-color: #f8d7da; }
            .online { color: #0c5460; background-color: #d1ecf1; }
            .offline { color: #856404; background-color: #fff3cd; }
            button { width: 100%; padding: 12px; font-size: 1em; border: none; border-radius: 6px; cursor: pointer; margin-top: 15px; }
            .btn-stop { background-color: #dc3545; color: white; }
            .btn-start { background-color: #28a745; color: white; }
            .btn-delete { background-color: #6c757d; color: white; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Panneau de Contrôle</h2>
            
            <p>Statut du script :<br>
                <span class="badge {{ 'running' if statut == 'RUNNING' else 'stop' }}">{{ statut }}</span>
            </p>
            
            <p>État de la machine :<br>
                <span class="badge {{ 'online' if pc_en_ligne else 'offline' }}">
                    {{ '🟢 En ligne (Allumé)' if pc_en_ligne else '🔴 Hors ligne (Éteint / Inactif)' }}
                </span>
            </p>
            
            <form action="/toggle" method="POST">
                {% if statut == 'RUNNING' %}
                    <button type="submit" class="btn-stop">🔴 Envoyer l'ordre d'ARRÊT</button>
                {% else %}
                    <button type="submit" class="btn-start">🟢 Relancer le script</button>
                {% endif %}
            </form>

            <form action="/supprimer-photos" method="POST" onsubmit="return confirm('Voulez-vous vraiment vider toutes les captures de la base de données ?');">
                <button type="submit" class="btn-delete">🗑️ Supprimer toutes les photos</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, statut=statut, pc_en_ligne=pc_en_ligne)

@app.route("/toggle", methods=["POST"])
def toggle():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT statut FROM controle_script WHERE id = 1;")
        actuel = cur.fetchone()[0]
        nouveau = "STOP" if actuel == "RUNNING" else "RUNNING"
        cur.execute("UPDATE controle_script SET statut = %s WHERE id = 1;", (nouveau,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur toggle : {e}")
    return redirect(url_for("index"))

@app.route("/supprimer-photos", methods=["POST"])
def supprimer_photos():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM captures_test;")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erreur suppression : {e}")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
