"""
gsc_connector.py — Conector GSC + Trends para Clivi SEO Motor
=============================================================
Corre cada domingo noche para actualizar los scores con datos reales.

Flujo:
1. GSC API → CTR real, posición, impresiones de clivi.com.mx
2. Google Trends → picos en tiempo real México
3. Recalcula scores con fórmula transaccional
4. Sube keywords priorizadas al KV de Cloudflare
5. El cron del lunes las procesa automáticamente

Uso:
    python gsc_connector.py              # GSC + Trends + sube al KV
    python gsc_connector.py --gsc-only   # solo GSC
    python gsc_connector.py --trends-only # solo Trends
    python gsc_connector.py --no-upload  # no sube al KV (solo imprime)

Requiere:
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client pytrends requests
"""

import argparse
import json
import pickle
import random
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
GSC_CREDS_FILE = BASE_DIR / "gsc-oauth.json"
GSC_TOKEN_FILE = BASE_DIR / "gsc-token.pickle"
SCORED_OUTPUT  = BASE_DIR / "keywords-scored.json"
BATCH_OUTPUT   = BASE_DIR / "trends_batch.json"
GSC_PROPERTY   = "sc-domain:clivi.com.mx"

CF_ACCOUNT_ID  = "5f4917c620a9cdaf5849cf1008dc93cf"
CF_KV_ID       = "2e6cee17ffad4d03b3aed30cf8fda716"

# ─── PESOS DE SCORING (priorizando transaccionalidad) ─────────────────────────
SCORING_WEIGHTS = {
    "intent":    0.35,
    "relevance": 0.25,
    "volume":    0.20,
    "ctr_opp":   0.12,
    "position":  0.08,
}

INTENT_SCORES = {
    "transactional": 100,
    "commercial":    80,
    "informational": 40,
}

# ─── BASE DE KEYWORDS ────────────────────────────────────────────────────────
KEYWORDS = [
    # glp1 - transaccional
    {"keyword": "semaglutida precio México",              "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 67000, "intent": "transactional", "relevance": 1.0},
    {"keyword": "ozempic precio México",                  "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 55000, "intent": "transactional", "relevance": 1.0},
    {"keyword": "tirzepatida precio en México",           "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 61000, "intent": "transactional", "relevance": 1.0},
    {"keyword": "mounjaro precio en México",              "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 61000, "intent": "transactional", "relevance": 1.0},
    {"keyword": "wegovy precio en México",                "topic": "peso",      "cluster": "medicamentos-peso",    "vol": 25000, "intent": "transactional", "relevance": 1.0},
    {"keyword": "saxenda precio en México",               "topic": "peso",      "cluster": "medicamentos-peso",    "vol": 20000, "intent": "transactional", "relevance": 1.0},
    # glp1 - informacional
    {"keyword": "semaglutida para qué sirve",             "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 95000, "intent": "informational", "relevance": 1.0},
    {"keyword": "ozempic para qué sirve",                 "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 80000, "intent": "informational", "relevance": 1.0},
    {"keyword": "tirzepatida para qué sirve",             "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 45000, "intent": "informational", "relevance": 1.0},
    {"keyword": "mounjaro para qué sirve",                "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 40000, "intent": "informational", "relevance": 1.0},
    {"keyword": "rybelsus para qué sirve",                "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 28000, "intent": "informational", "relevance": 1.0},
    {"keyword": "ozempic efectos secundarios",            "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 35000, "intent": "informational", "relevance": 1.0},
    {"keyword": "semaglutida vs tirzepatida",             "topic": "glucosa",   "cluster": "glp1-medicamentos",    "vol": 18000, "intent": "informational", "relevance": 1.0},
    {"keyword": "wegovy para qué sirve",                  "topic": "peso",      "cluster": "medicamentos-peso",    "vol": 30000, "intent": "informational", "relevance": 1.0},
    {"keyword": "saxenda para qué sirve",                 "topic": "peso",      "cluster": "medicamentos-peso",    "vol": 28000, "intent": "informational", "relevance": 1.0},
    {"keyword": "ozempic para bajar de peso sin diabetes","topic": "peso",      "cluster": "medicamentos-peso",    "vol": 30000, "intent": "informational", "relevance": 1.0},
    # tratamiento - comercial
    {"keyword": "tratamiento para diabetes tipo 2 en México",      "topic": "glucosa",   "cluster": "tratamiento-diabetes", "vol": 30000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "endocrinólogo para diabetes en línea",            "topic": "glucosa",   "cluster": "tratamiento-diabetes", "vol": 12000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "clínica para diabetes en México",                 "topic": "glucosa",   "cluster": "tratamiento-diabetes", "vol": 18000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "consulta médica diabetes online México",          "topic": "glucosa",   "cluster": "tratamiento-diabetes", "vol": 10000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "inyecciones para bajar de peso en México",        "topic": "peso",      "cluster": "medicamentos-peso",    "vol": 34000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "tratamiento médico para bajar de peso en México", "topic": "peso",      "cluster": "tratamiento-peso",     "vol": 28000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "médico para bajar de peso en línea",              "topic": "peso",      "cluster": "tratamiento-peso",     "vol": 15000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "endocrinólogo para bajar de peso",                "topic": "peso",      "cluster": "tratamiento-peso",     "vol": 18000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "tratamiento para bajar de peso sin cirugía",      "topic": "peso",      "cluster": "tratamiento-peso",     "vol": 22000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "clínica para bajar de peso en México",            "topic": "peso",      "cluster": "tratamiento-peso",     "vol": 12000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "obesidad mórbida tratamiento sin cirugía",        "topic": "peso",      "cluster": "condicion-obesidad",   "vol": 18000, "intent": "commercial", "relevance": 1.0},
    {"keyword": "nutrióloga en línea México",                      "topic": "meal-plan", "cluster": "alimentacion-peso",    "vol": 15000, "intent": "commercial", "relevance": 1.0},
    # antidiabéticos orales
    {"keyword": "metformina para qué sirve",                       "topic": "glucosa",   "cluster": "antidiabeticos-orales", "vol": 85000, "intent": "informational", "relevance": 1.0},
    {"keyword": "sitagliptina para qué sirve",                     "topic": "glucosa",   "cluster": "antidiabeticos-orales", "vol": 65000, "intent": "informational", "relevance": 1.0},
    {"keyword": "glibenclamida para qué sirve",                    "topic": "glucosa",   "cluster": "antidiabeticos-orales", "vol": 60000, "intent": "informational", "relevance": 1.0},
    {"keyword": "empagliflozina para qué sirve",                   "topic": "glucosa",   "cluster": "antidiabeticos-orales", "vol": 35000, "intent": "informational", "relevance": 1.0},
    {"keyword": "glipizida para qué sirve",                        "topic": "glucosa",   "cluster": "antidiabeticos-orales", "vol": 18000, "intent": "informational", "relevance": 1.0},
    # condición diabetes
    {"keyword": "síntomas diabetes tipo 2",                        "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 45000, "intent": "informational", "relevance": 0.8},
    {"keyword": "resistencia a la insulina tratamiento",           "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 22000, "intent": "informational", "relevance": 1.0},
    {"keyword": "cómo bajar la glucosa rápido",                    "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 55000, "intent": "informational", "relevance": 0.8},
    {"keyword": "prediabetes síntomas y tratamiento",              "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 25000, "intent": "informational", "relevance": 1.0},
    {"keyword": "valores normales de glucosa en sangre",           "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 40000, "intent": "informational", "relevance": 0.8},
    {"keyword": "hemoglobina glucosilada qué es",                  "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 28000, "intent": "informational", "relevance": 0.8},
    {"keyword": "resistencia a la insulina síntomas",              "topic": "glucosa",   "cluster": "condicion-diabetes",   "vol": 35000, "intent": "informational", "relevance": 0.8},
    # peso - condición
    {"keyword": "grasa visceral qué es y cómo eliminarla",         "topic": "peso",      "cluster": "condicion-obesidad",   "vol": 38000, "intent": "informational", "relevance": 0.8},
    {"keyword": "cómo bajar de peso con diabetes tipo 2",          "topic": "peso",      "cluster": "tratamiento-peso",     "vol": 25000, "intent": "informational", "relevance": 1.0},
    {"keyword": "por qué no bajo de peso aunque hago dieta",       "topic": "peso",      "cluster": "condicion-obesidad",   "vol": 42000, "intent": "informational", "relevance": 0.8},
    # meal-plan
    {"keyword": "plan de alimentación para diabéticos",            "topic": "meal-plan", "cluster": "alimentacion-diabetes","vol": 30000, "intent": "informational", "relevance": 0.8},
    {"keyword": "dieta para diabéticos qué pueden comer",          "topic": "meal-plan", "cluster": "alimentacion-diabetes","vol": 48000, "intent": "informational", "relevance": 0.6},
    {"keyword": "ayuno intermitente para diabéticos es seguro",    "topic": "meal-plan", "cluster": "alimentacion-peso",    "vol": 28000, "intent": "informational", "relevance": 0.6},
    # journey
    {"keyword": "cómo mejorar la sensibilidad a la insulina",      "topic": "journey",   "cluster": "habitos-metabolicos",  "vol": 20000, "intent": "informational", "relevance": 0.8},
    {"keyword": "hábitos para controlar la diabetes sin medicamento","topic": "journey",  "cluster": "habitos-metabolicos",  "vol": 22000, "intent": "informational", "relevance": 0.8},
    {"keyword": "ejercicio para bajar la glucosa",                 "topic": "journey",   "cluster": "ejercicio-glucosa",    "vol": 35000, "intent": "informational", "relevance": 0.6},
    {"keyword": "pérdida de peso sostenible sin efecto rebote",    "topic": "journey",   "cluster": "habitos-metabolicos",  "vol": 25000, "intent": "informational", "relevance": 0.8},
]

# ─── SCORING ─────────────────────────────────────────────────────────────────

def calculate_score(kw, gsc_data=None, trends_data=None):
    vol_norm     = min(100, (kw["vol"] / 100000) * 100)
    intent_score = INTENT_SCORES.get(kw["intent"], 40)
    relevance    = kw.get("relevance", 0.8) * 100
    ctr_opp      = 85
    pos_zone     = 70

    if gsc_data:
        row = gsc_data.get(kw["keyword"].lower())
        if row:
            ctr_opp  = max(0, 100 - (row["ctr"] * 100))
            pos      = row["position"]
            pos_zone = 20 if pos <= 3 else 100 if pos <= 10 else 60 if pos <= 20 else 10
            vol_norm = min(100, (row["impressions"] / 100000) * 100)

    trends_boost = 0
    if trends_data:
        for seed, score in trends_data.items():
            if seed.lower() in kw["keyword"].lower():
                trends_boost = min(15, int(score * 0.15))
                break

    raw = (
        intent_score * SCORING_WEIGHTS["intent"] +
        relevance    * SCORING_WEIGHTS["relevance"] +
        vol_norm     * SCORING_WEIGHTS["volume"] +
        ctr_opp      * SCORING_WEIGHTS["ctr_opp"] +
        pos_zone     * SCORING_WEIGHTS["position"]
    )
    return min(100, round(raw + trends_boost))

# ─── GSC ─────────────────────────────────────────────────────────────────────

def fetch_gsc_data():
    print("📊 Conectando a Google Search Console...")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        import googleapiclient.discovery

        SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
        creds  = None

        if GSC_TOKEN_FILE.exists():
            with open(GSC_TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow  = InstalledAppFlow.from_client_secrets_file(str(GSC_CREDS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            with open(GSC_TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

        service    = googleapiclient.discovery.build("searchconsole", "v1", credentials=creds)
        end_date   = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=GSC_PROPERTY,
            body={
                "startDate":  start_date,
                "endDate":    end_date,
                "dimensions": ["query"],
                "rowLimit":   5000,
                "dataState":  "final",
            }
        ).execute()

        rows = response.get("rows", [])
        print(f"  ✅ {len(rows)} keywords encontradas en GSC")

        gsc_data = {}
        for row in rows:
            query = row["keys"][0].lower()
            gsc_data[query] = {
                "clicks":      row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr":         row.get("ctr", 0),
                "position":    row.get("position", 50),
            }
        return gsc_data

    except Exception as e:
        print(f"  ⚠️  Error GSC: {e}")
        return {}

# ─── GOOGLE TRENDS ────────────────────────────────────────────────────────────

def fetch_trends_data():
    print("📈 Escaneando Google Trends México...")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="es-MX", tz=360)
        seeds    = ["ozempic", "semaglutida", "tirzepatida", "mounjaro", "wegovy", "diabetes tipo 2", "bajar de peso", "metformina"]
        scores   = {}

        for seed in seeds:
            try:
                pytrends.build_payload([seed], timeframe="today 1-m", geo="MX")
                data = pytrends.interest_over_time()
                if not data.empty and seed in data.columns:
                    scores[seed] = int(data[seed].mean())
                    print(f"  📊 {seed}: {scores[seed]}/100")
                time.sleep(random.uniform(6, 10))
            except Exception as e:
                print(f"  ⚠️  {seed}: {e}")
                scores[seed] = 0

        return scores
    except Exception as e:
        print(f"  ⚠️  Error Trends: {e}")
        return {}

# ─── SUBIR AL KV ─────────────────────────────────────────────────────────────

def upload_to_kv(keywords_for_kv):
    print("\n☁️  Subiendo keywords al KV de Cloudflare...")
    try:
        payload = json.dumps(keywords_for_kv, ensure_ascii=False)
        result  = subprocess.run([
            "pnpm", "wrangler", "kv", "key", "put",
            "--namespace-id", CF_KV_ID,
            "pending-keywords", payload,
            "--remote"
        ], capture_output=True, text=True, cwd=str(BASE_DIR))

        if result.returncode == 0:
            print(f"  ✅ {len(keywords_for_kv)} keywords subidas al KV")
            print(f"  El cron del lunes las procesará automáticamente")
        else:
            print(f"  ⚠️  Error subiendo al KV: {result.stderr[:300]}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Actualiza scores del motor SEO de Clivi")
    parser.add_argument("--gsc-only",    action="store_true", help="Solo GSC, sin Trends")
    parser.add_argument("--trends-only", action="store_true", help="Solo Trends, sin GSC")
    parser.add_argument("--no-upload",   action="store_true", help="No sube al KV")
    parser.add_argument("--top",         type=int, default=10, help="Top N para el batch")
    parser.add_argument("--property",    help="Propiedad GSC (ej: sc-domain:clivi.com.mx)")
    args = parser.parse_args()

    global GSC_PROPERTY
    if args.property:
        GSC_PROPERTY = args.property

    print(f"\n🚀 Clivi SEO Motor — Actualización de scores")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    gsc_data    = {}
    trends_data = {}

    if not args.trends_only:
        gsc_data = fetch_gsc_data()

    if not args.gsc_only:
        trends_data = fetch_trends_data()

    print("\n📐 Calculando scores...")
    scored = []
    for kw in KEYWORDS:
        score    = calculate_score(kw, gsc_data, trends_data)
        kw_copy  = dict(kw)
        kw_copy["score"] = score

        gsc_row = gsc_data.get(kw["keyword"].lower())
        if gsc_row:
            kw_copy["gsc_clicks"]      = gsc_row["clicks"]
            kw_copy["gsc_impressions"] = gsc_row["impressions"]
            kw_copy["gsc_ctr"]         = round(gsc_row["ctr"] * 100, 2)
            kw_copy["gsc_position"]    = round(gsc_row["position"], 1)
            kw_copy["has_gsc_data"]    = True
        else:
            kw_copy["has_gsc_data"] = False

        for seed, ts in trends_data.items():
            if seed.lower() in kw["keyword"].lower() and ts > 20:
                kw_copy["trending"]     = True
                kw_copy["trends_score"] = ts
                break

        scored.append(kw_copy)

    scored.sort(key=lambda x: (
        -INTENT_SCORES.get(x["intent"], 40),
        -x.get("relevance", 0.8),
        -x["score"]
    ))

    SCORED_OUTPUT.write_text(json.dumps(scored, indent=2, ensure_ascii=False))
    print(f"  ✅ Scores guardados: {SCORED_OUTPUT}")

    print(f"\n{'='*60}")
    print(f"TOP KEYWORDS POR SCORE (fórmula transaccional)")
    print(f"{'='*60}")
    for i, kw in enumerate(scored[:20], 1):
        gsc_flag   = "📊" if kw.get("has_gsc_data") else "  "
        trend_flag = "📈" if kw.get("trending") else "  "
        intent_e   = "💰" if kw["intent"] == "transactional" else "🛒" if kw["intent"] == "commercial" else "ℹ️"
        print(f"{i:2}. [{kw['score']:3}/100] {gsc_flag}{trend_flag} {intent_e} {kw['keyword'][:50]}")

    # Generar batch para el worker con diversificación por cluster
    cluster_count = {}
    batch = []
    for kw in scored:
        if len(batch) >= args.top:
            break
        c = kw["cluster"]
        if cluster_count.get(c, 0) < 3:
            cluster_count[c] = cluster_count.get(c, 0) + 1
            batch.append({
                "keyword":          kw["keyword"],
                "intent":           kw["intent"],
                "topic":            kw["topic"],
                "variant":          "article",
                "monthly_searches": kw["vol"],
                "extra_tags":       [kw["topic"], kw["cluster"]],
            })

    BATCH_OUTPUT.write_text(json.dumps({"keywords": batch}, indent=2, ensure_ascii=False))
    print(f"\n✅ Batch de {len(batch)} keywords guardado: {BATCH_OUTPUT}")

    with_gsc   = sum(1 for k in scored if k.get("has_gsc_data"))
    trending   = sum(1 for k in scored if k.get("trending"))
    transac    = sum(1 for k in scored if k["intent"] == "transactional")
    commercial = sum(1 for k in scored if k["intent"] == "commercial")

    print(f"\n📊 Estadísticas:")
    print(f"   Total keywords:    {len(scored)}")
    print(f"   Con datos GSC:     {with_gsc}")
    print(f"   Trending ahorita:  {trending}")
    print(f"   Transaccionales:   {transac}")
    print(f"   Comerciales:       {commercial}")
    print(f"   Informacionales:   {len(scored) - transac - commercial}")

    if not args.no_upload:
        upload_to_kv(batch)

if __name__ == "__main__":
    main()
