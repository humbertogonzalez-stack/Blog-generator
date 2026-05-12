"""
dashboard.py — Clivi SEO Intelligence Dashboard
================================================
App web local para visualizar y gestionar el motor de keywords de Clivi.

Características:
- Grafo interactivo de clusters y keywords
- Integración con Google Trends en tiempo real
- Score de cada keyword con breakdown de factores
- Estado de artículos generados (pendiente/generado/publicado)
- Generación de artículos con un click

Uso:
    python dashboard.py
    Abre http://localhost:5000 en tu navegador

Requiere:
    pip install flask flask-cors plotly networkx requests pytrends
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import json, random, time, threading, os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
EMDASH_BASE_URL = "https://clivi-blog-staging.santiago-arboleda.workers.dev"
EMDASH_TOKEN    = "ec_pat_bR3tjVtM6nAOKF0Ap160he33Cz06vHxHBbb8TKX3lXw"
WORKER_URL      = "http://127.0.0.1:8787"
WORKER_SECRET   = "local-test-secret-123"
STATE_FILE      = Path(__file__).parent / "dashboard_state.json"

# ─── BASE DE KEYWORDS ────────────────────────────────────────────────────────
KEYWORDS = [
    # glucosa - glp1
    {"keyword": "semaglutida para qué sirve", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 95000, "intent": "informational", "score": 87},
    {"keyword": "semaglutida precio México", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 67000, "intent": "transactional", "score": 92},
    {"keyword": "ozempic para qué sirve", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 80000, "intent": "informational", "score": 85},
    {"keyword": "ozempic precio México", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 55000, "intent": "transactional", "score": 90},
    {"keyword": "tirzepatida para qué sirve", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 45000, "intent": "informational", "score": 83},
    {"keyword": "tirzepatida precio en México", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 61000, "intent": "transactional", "score": 91},
    {"keyword": "mounjaro precio en México", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 61000, "intent": "transactional", "score": 91},
    {"keyword": "mounjaro para qué sirve", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 40000, "intent": "informational", "score": 82},
    {"keyword": "ozempic efectos secundarios", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 35000, "intent": "informational", "score": 78},
    {"keyword": "semaglutida vs tirzepatida", "topic": "glucosa", "cluster": "glp1-medicamentos", "vol": 18000, "intent": "informational", "score": 74},
    # glucosa - antidiabéticos
    {"keyword": "metformina para qué sirve", "topic": "glucosa", "cluster": "antidiabeticos-orales", "vol": 85000, "intent": "informational", "score": 84},
    {"keyword": "sitagliptina para qué sirve", "topic": "glucosa", "cluster": "antidiabeticos-orales", "vol": 65000, "intent": "informational", "score": 81},
    {"keyword": "glibenclamida para qué sirve", "topic": "glucosa", "cluster": "antidiabeticos-orales", "vol": 60000, "intent": "informational", "score": 80},
    {"keyword": "empagliflozina para qué sirve", "topic": "glucosa", "cluster": "antidiabeticos-orales", "vol": 35000, "intent": "informational", "score": 76},
    {"keyword": "glipizida para qué sirve", "topic": "glucosa", "cluster": "antidiabeticos-orales", "vol": 18000, "intent": "informational", "score": 70},
    # glucosa - condición
    {"keyword": "síntomas diabetes tipo 2", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 45000, "intent": "informational", "score": 72},
    {"keyword": "qué es la prediabetes", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 32000, "intent": "informational", "score": 70},
    {"keyword": "resistencia a la insulina síntomas", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 35000, "intent": "informational", "score": 71},
    {"keyword": "resistencia a la insulina tratamiento", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 22000, "intent": "informational", "score": 74},
    {"keyword": "glucosa en ayunas normal rango", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 42000, "intent": "informational", "score": 73},
    {"keyword": "cómo bajar la glucosa rápido", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 55000, "intent": "informational", "score": 75},
    {"keyword": "hemoglobina glucosilada qué es", "topic": "glucosa", "cluster": "condicion-diabetes", "vol": 28000, "intent": "informational", "score": 69},
    # glucosa - tratamiento
    {"keyword": "tratamiento para diabetes tipo 2 en México", "topic": "glucosa", "cluster": "tratamiento-diabetes", "vol": 30000, "intent": "commercial", "score": 86},
    {"keyword": "endocrinólogo para diabetes en línea", "topic": "glucosa", "cluster": "tratamiento-diabetes", "vol": 12000, "intent": "commercial", "score": 84},
    {"keyword": "clínica para diabetes en México", "topic": "glucosa", "cluster": "tratamiento-diabetes", "vol": 18000, "intent": "commercial", "score": 85},
    # peso - medicamentos
    {"keyword": "wegovy para qué sirve", "topic": "peso", "cluster": "medicamentos-peso", "vol": 30000, "intent": "informational", "score": 82},
    {"keyword": "wegovy precio en México", "topic": "peso", "cluster": "medicamentos-peso", "vol": 25000, "intent": "transactional", "score": 88},
    {"keyword": "saxenda para qué sirve", "topic": "peso", "cluster": "medicamentos-peso", "vol": 28000, "intent": "informational", "score": 81},
    {"keyword": "inyecciones para bajar de peso en México", "topic": "peso", "cluster": "medicamentos-peso", "vol": 34000, "intent": "commercial", "score": 87},
    {"keyword": "ozempic para bajar de peso sin diabetes", "topic": "peso", "cluster": "medicamentos-peso", "vol": 30000, "intent": "informational", "score": 80},
    # peso - condición
    {"keyword": "obesidad mórbida tratamiento sin cirugía", "topic": "peso", "cluster": "condicion-obesidad", "vol": 18000, "intent": "commercial", "score": 85},
    {"keyword": "grasa visceral qué es y cómo eliminarla", "topic": "peso", "cluster": "condicion-obesidad", "vol": 38000, "intent": "informational", "score": 74},
    {"keyword": "por qué no bajo de peso aunque hago dieta", "topic": "peso", "cluster": "condicion-obesidad", "vol": 42000, "intent": "informational", "score": 73},
    # peso - tratamiento
    {"keyword": "tratamiento médico para bajar de peso en México", "topic": "peso", "cluster": "tratamiento-peso", "vol": 28000, "intent": "commercial", "score": 89},
    {"keyword": "médico para bajar de peso en línea", "topic": "peso", "cluster": "tratamiento-peso", "vol": 15000, "intent": "commercial", "score": 86},
    {"keyword": "endocrinólogo para bajar de peso", "topic": "peso", "cluster": "tratamiento-peso", "vol": 18000, "intent": "commercial", "score": 87},
    {"keyword": "cómo bajar de peso con diabetes tipo 2", "topic": "peso", "cluster": "tratamiento-peso", "vol": 25000, "intent": "informational", "score": 78},
    # meal-plan
    {"keyword": "dieta para diabéticos qué pueden comer", "topic": "meal-plan", "cluster": "alimentacion-diabetes", "vol": 48000, "intent": "informational", "score": 73},
    {"keyword": "alimentos que suben la glucosa rápido", "topic": "meal-plan", "cluster": "alimentacion-diabetes", "vol": 38000, "intent": "informational", "score": 70},
    {"keyword": "plan de alimentación para diabéticos", "topic": "meal-plan", "cluster": "alimentacion-diabetes", "vol": 30000, "intent": "informational", "score": 72},
    {"keyword": "ayuno intermitente para diabéticos es seguro", "topic": "meal-plan", "cluster": "alimentacion-peso", "vol": 28000, "intent": "informational", "score": 69},
    {"keyword": "nutrióloga en línea México", "topic": "meal-plan", "cluster": "alimentacion-peso", "vol": 15000, "intent": "commercial", "score": 82},
    # journey
    {"keyword": "ejercicio para bajar la glucosa", "topic": "journey", "cluster": "ejercicio-glucosa", "vol": 35000, "intent": "informational", "score": 68},
    {"keyword": "caminar después de comer glucosa", "topic": "journey", "cluster": "ejercicio-glucosa", "vol": 28000, "intent": "informational", "score": 66},
    {"keyword": "cómo mejorar la sensibilidad a la insulina", "topic": "journey", "cluster": "habitos-metabolicos", "vol": 20000, "intent": "informational", "score": 70},
    {"keyword": "hábitos para controlar la diabetes sin medicamento", "topic": "journey", "cluster": "habitos-metabolicos", "vol": 22000, "intent": "informational", "score": 71},
    {"keyword": "pérdida de peso sostenible sin efecto rebote", "topic": "journey", "cluster": "habitos-metabolicos", "vol": 25000, "intent": "informational", "score": 72},
]

TOPIC_COLORS = {
    "glucosa":   "#185FA5",
    "peso":      "#0F6E56",
    "meal-plan": "#BA7517",
    "journey":   "#993556",
}

CLUSTER_COLORS = {
    "glp1-medicamentos":    "#378ADD",
    "antidiabeticos-orales":"#53C4A0",
    "condicion-diabetes":   "#7F77DD",
    "tratamiento-diabetes": "#185FA5",
    "medicamentos-peso":    "#1D9E75",
    "condicion-obesidad":   "#5DCAA5",
    "tratamiento-peso":     "#0F6E56",
    "alimentacion-diabetes":"#EF9F27",
    "alimentacion-peso":    "#BA7517",
    "ejercicio-glucosa":    "#D4537E",
    "habitos-metabolicos":  "#993556",
}

# ─── ESTADO ──────────────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except: pass
    return {"generated": [], "trending": [], "last_trends_scan": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

state = load_state()

# ─── TRENDS ──────────────────────────────────────────────────────────────────
trends_cache = {}
trends_lock = threading.Lock()

def fetch_trends_async():
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="es-MX", tz=360)
        seeds = ["ozempic", "diabetes tipo 2", "bajar de peso", "semaglutida", "metformina"]
        scores = {}
        for seed in seeds:
            try:
                pytrends.build_payload([seed], timeframe="today 1-m", geo="MX")
                data = pytrends.interest_over_time()
                if not data.empty and seed in data.columns:
                    scores[seed] = int(data[seed].mean())
                time.sleep(random.uniform(5, 8))
            except: 
                scores[seed] = 0
        with trends_lock:
            trends_cache.update(scores)
            state["last_trends_scan"] = datetime.now().isoformat()
            state["trending"] = [k for k, v in sorted(scores.items(), key=lambda x: -x[1]) if v > 20]
            save_state(state)
    except Exception as e:
        print(f"Trends error: {e}")

# ─── RUTAS ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/keywords")
def api_keywords():
    generated_slugs = set(state.get("generated", []))
    result = []
    for kw in KEYWORDS:
        slug = kw["keyword"].lower().replace(" ", "-")
        slug = "".join(c if c.isalnum() or c == "-" else "" for c in 
                      slug.encode("ascii", "ignore").decode())
        kw_copy = dict(kw)
        kw_copy["slug"] = slug
        kw_copy["status"] = "generated" if slug in generated_slugs else "pending"
        # Boost score si está trending
        trending = state.get("trending", [])
        for t in trending:
            if t.lower() in kw["keyword"].lower():
                kw_copy["score"] = min(100, kw["score"] + 15)
                kw_copy["trending"] = True
                break
        result.append(kw_copy)
    return jsonify(result)

@app.route("/api/stats")
def api_stats():
    generated = len(state.get("generated", []))
    total = len(KEYWORDS)
    by_topic = {}
    for kw in KEYWORDS:
        t = kw["topic"]
        by_topic[t] = by_topic.get(t, 0) + 1
    return jsonify({
        "total": total,
        "generated": generated,
        "pending": total - generated,
        "coverage": round(generated / total * 100, 1),
        "by_topic": by_topic,
        "trending": state.get("trending", []),
        "last_scan": state.get("last_trends_scan"),
    })

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.json
    keyword = data.get("keyword")
    topic = data.get("topic", "glucosa")
    intent = data.get("intent", "informational")
    
    try:
        import requests as req
        res = req.post(
            f"{WORKER_URL}/{WORKER_SECRET}/generate",
            json={"keywords": [{"keyword": keyword, "topic": topic, "intent": intent}]},
            timeout=120
        )
        if res.ok:
            result = res.json()
            if result.get("ok", 0) > 0:
                slug = keyword.lower().replace(" ", "-")
                slug = "".join(c if c.isalnum() or c == "-" else "" 
                              for c in slug.encode("ascii", "ignore").decode())
                state["generated"].append(slug)
                save_state(state)
                return jsonify({"ok": True, "result": result})
        return jsonify({"ok": False, "error": res.text[:200]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/scan-trends", methods=["POST"])
def api_scan_trends():
    t = threading.Thread(target=fetch_trends_async, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Escaneando Google Trends... (~3 min)"})

@app.route("/api/graph")
def api_graph():
    nodes = []
    edges = []
    node_id = {}
    
    topics = list(set(kw["topic"] for kw in KEYWORDS))
    for i, topic in enumerate(topics):
        nid = f"topic_{topic}"
        node_id[nid] = len(nodes)
        nodes.append({
            "id": nid, "label": topic, "type": "topic",
            "color": TOPIC_COLORS.get(topic, "#888"),
            "size": 30
        })
    
    clusters = list(set(kw["cluster"] for kw in KEYWORDS))
    for cluster in clusters:
        topic = next(kw["topic"] for kw in KEYWORDS if kw["cluster"] == cluster)
        nid = f"cluster_{cluster}"
        node_id[nid] = len(nodes)
        nodes.append({
            "id": nid, "label": cluster.replace("-", " "), "type": "cluster",
            "color": CLUSTER_COLORS.get(cluster, "#aaa"),
            "size": 18
        })
        edges.append({"from": f"topic_{topic}", "to": nid, "weight": 2})
    
    generated_slugs = set(state.get("generated", []))
    trending = state.get("trending", [])
    
    for kw in KEYWORDS:
        slug = kw["keyword"].lower().replace(" ", "-")
        slug = "".join(c if c.isalnum() or c == "-" else "" 
                      for c in slug.encode("ascii", "ignore").decode())
        is_generated = slug in generated_slugs
        is_trending = any(t.lower() in kw["keyword"].lower() for t in trending)
        nid = f"kw_{slug}"
        node_id[nid] = len(nodes)
        nodes.append({
            "id": nid,
            "label": kw["keyword"],
            "type": "keyword",
            "color": "#22c55e" if is_generated else ("#f59e0b" if is_trending else "#6b7280"),
            "size": max(8, int(kw["score"] / 10)),
            "score": kw["score"],
            "topic": kw["topic"],
            "intent": kw["intent"],
            "vol": kw["vol"],
            "status": "generated" if is_generated else ("trending" if is_trending else "pending"),
            "slug": slug,
        })
        edges.append({"from": f"cluster_{kw['cluster']}", "to": nid, "weight": 1})
    
    return jsonify({"nodes": nodes, "edges": edges})

# ─── HTML ─────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clivi SEO Intelligence</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/dist/vis-network.min.css" rel="stylesheet"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}
.header{background:#1a1d2e;border-bottom:1px solid #2d3748;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:18px;font-weight:700;color:#a78bfa}
.logo span{color:#e2e8f0;font-weight:400}
.nav{display:flex;gap:8px}
.nav-btn{background:none;border:1px solid #374151;color:#9ca3af;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;transition:all .2s}
.nav-btn.active,.nav-btn:hover{background:#374151;color:#e2e8f0}
.main{display:flex;height:calc(100vh - 57px)}
.sidebar{width:300px;background:#1a1d2e;border-right:1px solid #2d3748;overflow-y:auto;flex-shrink:0}
.content{flex:1;overflow:hidden;position:relative}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:16px}
.stat-card{background:#242840;border:1px solid #2d3748;border-radius:8px;padding:14px}
.stat-val{font-size:28px;font-weight:700;color:#a78bfa}
.stat-label{font-size:12px;color:#6b7280;margin-top:2px}
.section-title{font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;padding:12px 16px 6px}
.kw-item{padding:10px 16px;border-bottom:1px solid #1e2235;cursor:pointer;transition:background .15s}
.kw-item:hover{background:#242840}
.kw-item.selected{background:#2d2f4a}
.kw-name{font-size:13px;color:#e2e8f0;margin-bottom:3px}
.kw-meta{display:flex;gap:6px;align-items:center}
.badge{font-size:10px;padding:2px 7px;border-radius:10px;font-weight:500}
.badge-glucosa{background:#1e3a5f;color:#60a5fa}
.badge-peso{background:#1a3a2e;color:#34d399}
.badge-meal-plan{background:#3d2e00;color:#fbbf24}
.badge-journey{background:#3d1a2e;color:#f472b6}
.badge-generated{background:#14532d;color:#4ade80}
.badge-trending{background:#451a03;color:#fb923c}
.badge-pending{background:#1f2937;color:#6b7280}
.score-bar{height:3px;background:#374151;border-radius:2px;margin-top:6px;overflow:hidden}
.score-fill{height:100%;background:linear-gradient(90deg,#6366f1,#a78bfa);border-radius:2px;transition:width .3s}
#graph-container{width:100%;height:100%;background:#0d0f1a}
.panel{display:none;height:100%;overflow-y:auto;padding:20px}
.panel.active{display:block}
#graph-panel{display:none;height:100%}
#graph-panel.active{display:block}
.detail-panel{position:absolute;top:16px;right:16px;width:280px;background:#1a1d2e;border:1px solid #2d3748;border-radius:10px;padding:16px;z-index:100;display:none}
.detail-panel.show{display:block}
.detail-title{font-size:14px;font-weight:600;color:#e2e8f0;margin-bottom:8px}
.detail-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1e2235;font-size:12px}
.detail-row:last-child{border:none}
.detail-key{color:#6b7280}
.detail-val{color:#e2e8f0;font-weight:500}
.btn-generate{width:100%;background:#6366f1;border:none;color:#fff;padding:10px;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;margin-top:12px;transition:background .2s}
.btn-generate:hover{background:#4f46e5}
.btn-generate:disabled{background:#374151;color:#6b7280;cursor:not-allowed}
.btn-scan{background:#1e3a2e;border:1px solid #065f46;color:#34d399;padding:8px 14px;border-radius:6px;font-size:12px;cursor:pointer;width:100%;margin:8px 16px;width:calc(100% - 32px);transition:all .2s}
.btn-scan:hover{background:#065f46}
.trend-chip{display:inline-block;background:#451a03;color:#fb923c;font-size:11px;padding:3px 8px;border-radius:10px;margin:2px}
.toast{position:fixed;bottom:20px;right:20px;background:#1a1d2e;border:1px solid #374151;padding:12px 18px;border-radius:8px;font-size:13px;z-index:999;display:none;max-width:300px}
.toast.show{display:block}
.filter-bar{padding:10px 16px;border-bottom:1px solid #2d3748;display:flex;gap:6px;flex-wrap:wrap}
.filter-btn{background:#1e2235;border:1px solid #2d3748;color:#9ca3af;padding:4px 10px;border-radius:12px;font-size:11px;cursor:pointer;transition:all .15s}
.filter-btn.active{border-color:#6366f1;color:#a78bfa;background:#1e1e3f}
.search-box{width:100%;background:#242840;border:1px solid #374151;color:#e2e8f0;padding:8px 12px;border-radius:6px;font-size:13px;margin:10px 16px;width:calc(100% - 32px)}
.search-box:focus{outline:none;border-color:#6366f1}
.legend{position:absolute;bottom:16px;left:16px;background:#1a1d2edd;border:1px solid #2d3748;border-radius:8px;padding:10px 14px;font-size:11px;z-index:100}
.legend-item{display:flex;align-items:center;gap:6px;margin:3px 0;color:#9ca3af}
.legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
</style>
</head>
<body>
<div class="header">
  <div class="logo">Clivi <span>SEO Intelligence</span></div>
  <div class="nav">
    <button class="nav-btn active" onclick="showPanel('keywords')">Keywords</button>
    <button class="nav-btn" onclick="showPanel('graph')">Grafo</button>
    <button class="nav-btn" onclick="showPanel('trends')">Trends</button>
  </div>
</div>
<div class="main">
  <div class="sidebar">
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-val" id="stat-total">-</div><div class="stat-label">Total keywords</div></div>
      <div class="stat-card"><div class="stat-val" id="stat-generated" style="color:#4ade80">-</div><div class="stat-label">Generadas</div></div>
      <div class="stat-card"><div class="stat-val" id="stat-pending" style="color:#fb923c">-</div><div class="stat-label">Pendientes</div></div>
      <div class="stat-card"><div class="stat-val" id="stat-coverage" style="color:#60a5fa">-</div><div class="stat-label">Cobertura</div></div>
    </div>
    
    <div id="trending-section" style="padding:0 16px 8px">
      <div class="section-title">📈 Trending ahora</div>
      <div id="trending-chips"><span style="font-size:12px;color:#6b7280">Corre el scanner para ver tendencias</span></div>
    </div>

    <button class="btn-scan" onclick="scanTrends()">🔍 Escanear Google Trends</button>
    
    <input type="text" class="search-box" id="search-box" placeholder="Buscar keyword..." oninput="filterKeywords()">
    
    <div class="filter-bar" id="filter-bar">
      <button class="filter-btn active" onclick="setFilter('all')">Todas</button>
      <button class="filter-btn" onclick="setFilter('pending')">Pendientes</button>
      <button class="filter-btn" onclick="setFilter('generated')">Generadas</button>
      <button class="filter-btn" onclick="setFilter('trending')">Trending</button>
      <button class="filter-btn" onclick="setFilter('glucosa')">Glucosa</button>
      <button class="filter-btn" onclick="setFilter('peso')">Peso</button>
      <button class="filter-btn" onclick="setFilter('meal-plan')">Nutrición</button>
      <button class="filter-btn" onclick="setFilter('journey')">Movimiento</button>
    </div>
    
    <div id="kw-list"></div>
  </div>
  
  <div class="content">
    <div id="keywords-panel" class="panel active">
      <div id="kw-detail-empty" style="display:flex;align-items:center;justify-content:center;height:100%;color:#4b5563;font-size:14px">
        Selecciona una keyword del panel izquierdo
      </div>
    </div>
    
    <div id="graph-panel">
      <div id="graph-container"></div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:#4ade80"></div>Generada</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div>Trending</div>
        <div class="legend-item"><div class="legend-dot" style="background:#6b7280"></div>Pendiente</div>
      </div>
    </div>
    
    <div id="trends-panel" class="panel">
      <h2 style="font-size:16px;font-weight:600;margin-bottom:16px">Google Trends — México</h2>
      <div id="trends-content" style="color:#6b7280;font-size:14px">
        Presiona "Escanear Google Trends" para obtener datos en tiempo real.
        El scan toma ~3 minutos para evitar bloqueos de Google.
      </div>
    </div>
    
    <div class="detail-panel" id="detail-panel">
      <div class="detail-title" id="detail-title">—</div>
      <div id="detail-rows"></div>
      <button class="btn-generate" id="btn-generate" onclick="generateSelected()">
        ⚡ Generar artículo
      </button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
let keywords = [];
let selectedKw = null;
let network = null;
let currentFilter = 'all';
let searchQuery = '';

async function loadData() {
  const [kws, stats] = await Promise.all([
    fetch('/api/keywords').then(r => r.json()),
    fetch('/api/stats').then(r => r.json())
  ]);
  keywords = kws;
  
  document.getElementById('stat-total').textContent = stats.total;
  document.getElementById('stat-generated').textContent = stats.generated;
  document.getElementById('stat-pending').textContent = stats.pending;
  document.getElementById('stat-coverage').textContent = stats.coverage + '%';
  
  if (stats.trending && stats.trending.length > 0) {
    document.getElementById('trending-chips').innerHTML = 
      stats.trending.map(t => `<span class="trend-chip">${t}</span>`).join('');
  }
  
  if (stats.last_scan) {
    const d = new Date(stats.last_scan);
    document.getElementById('trends-content').innerHTML = 
      `<p style="color:#6b7280;font-size:12px;margin-bottom:12px">Último scan: ${d.toLocaleString('es-MX')}</p>
       <div style="display:flex;flex-wrap:wrap;gap:8px">` +
      (stats.trending || []).map(t => 
        `<span style="background:#451a03;color:#fb923c;padding:6px 12px;border-radius:6px;font-size:13px">${t}</span>`
      ).join('') + '</div>';
  }
  
  renderKeywordList();
}

function renderKeywordList() {
  const list = document.getElementById('kw-list');
  const filtered = keywords.filter(kw => {
    const matchFilter = currentFilter === 'all' || 
      kw.status === currentFilter || kw.topic === currentFilter;
    const matchSearch = !searchQuery || 
      kw.keyword.toLowerCase().includes(searchQuery.toLowerCase());
    return matchFilter && matchSearch;
  });
  
  list.innerHTML = filtered.map(kw => `
    <div class="kw-item ${selectedKw?.keyword === kw.keyword ? 'selected' : ''}" 
         onclick="selectKeyword(${JSON.stringify(kw).replace(/"/g, '&quot;')})">
      <div class="kw-name">${kw.keyword}</div>
      <div class="kw-meta">
        <span class="badge badge-${kw.topic}">${kw.topic}</span>
        <span class="badge badge-${kw.status}">${kw.status === 'generated' ? '✓ generada' : kw.status === 'trending' ? '📈 trending' : 'pendiente'}</span>
        <span style="font-size:11px;color:#6b7280;margin-left:auto">${kw.score}/100</span>
      </div>
      <div class="score-bar"><div class="score-fill" style="width:${kw.score}%"></div></div>
    </div>
  `).join('');
}

function selectKeyword(kw) {
  selectedKw = kw;
  renderKeywordList();
  
  const panel = document.getElementById('detail-panel');
  panel.classList.add('show');
  document.getElementById('detail-title').textContent = kw.keyword;
  
  const rows = [
    ['Topic', kw.topic],
    ['Cluster', kw.cluster],
    ['Intención', kw.intent],
    ['Volumen/mes', kw.vol?.toLocaleString() || '—'],
    ['Score', kw.score + '/100'],
    ['Estado', kw.status],
  ];
  
  document.getElementById('detail-rows').innerHTML = rows.map(([k,v]) => 
    `<div class="detail-row"><span class="detail-key">${k}</span><span class="detail-val">${v}</span></div>`
  ).join('');
  
  const btn = document.getElementById('btn-generate');
  if (kw.status === 'generated') {
    btn.textContent = '✓ Ya generado';
    btn.disabled = true;
  } else {
    btn.textContent = '⚡ Generar artículo';
    btn.disabled = false;
  }
}

async function generateSelected() {
  if (!selectedKw) return;
  const btn = document.getElementById('btn-generate');
  btn.textContent = '⏳ Generando...';
  btn.disabled = true;
  
  showToast('Generando "' + selectedKw.keyword + '"... esto tarda ~1 min');
  
  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      keyword: selectedKw.keyword,
      topic: selectedKw.topic,
      intent: selectedKw.intent
    })
  }).then(r => r.json());
  
  if (res.ok) {
    showToast('✅ Artículo generado y enviado a Emdash');
    await loadData();
    if (selectedKw) selectKeyword({...selectedKw, status: 'generated'});
  } else {
    showToast('❌ Error: ' + (res.error || 'desconocido'));
    btn.textContent = '⚡ Generar artículo';
    btn.disabled = false;
  }
}

async function scanTrends() {
  showToast('Iniciando scan de Google Trends... (~3 min)');
  await fetch('/api/scan-trends', {method: 'POST'});
  setTimeout(loadData, 180000);
}

function setFilter(f) {
  currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  renderKeywordList();
}

function filterKeywords() {
  searchQuery = document.getElementById('search-box').value;
  renderKeywordList();
}

function showPanel(name) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  
  document.getElementById('keywords-panel').classList.remove('active');
  document.getElementById('graph-panel').classList.remove('active');
  document.getElementById('trends-panel').classList.remove('active');
  
  if (name === 'keywords') {
    document.getElementById('keywords-panel').classList.add('active');
  } else if (name === 'graph') {
    document.getElementById('graph-panel').classList.add('active');
    initGraph();
  } else if (name === 'trends') {
    document.getElementById('trends-panel').classList.add('active');
  }
}

async function initGraph() {
  if (network) return;
  const data = await fetch('/api/graph').then(r => r.json());
  
  const nodes = new vis.DataSet(data.nodes.map(n => ({
    id: n.id,
    label: n.type === 'keyword' ? n.label.substring(0, 30) : n.label,
    color: { background: n.color, border: n.color, highlight: { background: '#fff', border: n.color } },
    size: n.size,
    font: { color: '#e2e8f0', size: n.type === 'topic' ? 14 : n.type === 'cluster' ? 12 : 10 },
    title: n.label + (n.score ? ` (score: ${n.score})` : ''),
    shape: n.type === 'topic' ? 'hexagon' : n.type === 'cluster' ? 'diamond' : 'dot',
    data: n,
  })));
  
  const edges = new vis.DataSet(data.edges.map((e, i) => ({
    id: i, from: e.from, to: e.to,
    color: { color: '#2d3748', highlight: '#6366f1' },
    width: e.weight * 0.5,
  })));
  
  const container = document.getElementById('graph-container');
  network = new vis.Network(container, { nodes, edges }, {
    physics: { stabilization: { iterations: 100 }, barnesHut: { gravitationalConstant: -3000, springLength: 120 } },
    interaction: { hover: true, tooltipDelay: 100 },
    layout: { improvedLayout: true },
  });
  
  network.on('click', params => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const node = data.nodes.find(n => n.id === nodeId);
      if (node && node.type === 'keyword') {
        const kw = keywords.find(k => k.keyword === node.label || node.label.startsWith(k.keyword.substring(0, 25)));
        if (kw) {
          showPanel('keywords');
          document.querySelectorAll('.nav-btn')[0].classList.add('active');
          document.querySelectorAll('.nav-btn')[1].classList.remove('active');
          selectKeyword(kw);
        }
      }
    }
  });
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 4000);
}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("\n🚀 Clivi SEO Intelligence Dashboard")
    print("   Abre http://localhost:5000 en tu navegador\n")
    app.run(debug=False, port=5000, host="0.0.0.0")
