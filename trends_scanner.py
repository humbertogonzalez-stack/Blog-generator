"""
trends_scanner.py
=================
Escanea Google Trends en México para detectar keywords relacionadas a Clivi
que estén teniendo un pico de búsqueda en tiempo real.

Mejoras anti-bloqueo:
- Pausa larga entre pilares (30s)
- Pausa media entre chunks (8s)
- Reintentos automáticos con backoff exponencial
- Solo 1 keyword por request para reducir detección

Uso:
    python trends_scanner.py                     # escanea todo
    python trends_scanner.py --topic glucosa     # solo un pilar
    python trends_scanner.py --top 5             # top 5 keywords
    python trends_scanner.py --output batch.json # nombre del archivo de salida

Requiere:
    pip install pytrends
"""

import argparse
import json
import time
import random
from datetime import datetime

try:
    from pytrends.request import TrendReq
except ImportError:
    print("Error: instala pytrends con: pip install pytrends")
    exit(1)


KEYWORD_UNIVERSE = {
    "glucosa": [
        "semaglutida", "ozempic", "tirzepatida", "mounjaro",
        "metformina", "sitagliptina", "glibenclamida",
        "diabetes tipo 2", "prediabetes", "glucosa alta",
    ],
    "peso": [
        "wegovy", "saxenda", "bajar de peso",
        "obesidad tratamiento", "inyecciones adelgazar",
        "tratamiento obesidad sin cirugia",
    ],
    "meal-plan": [
        "dieta para diabeticos", "plan alimenticio diabetes",
        "nutriologa en linea", "ayuno intermitente diabetes",
    ],
    "journey": [
        "ejercicio bajar glucosa", "habitos diabetes",
        "perder peso sin rebote",
    ],
}

INTENT_MAP = {
    "semaglutida": "informational", "ozempic": "informational",
    "tirzepatida": "informational", "mounjaro": "transactional",
    "wegovy": "informational", "saxenda": "informational",
    "metformina": "informational", "sitagliptina": "informational",
    "glibenclamida": "informational",
    "bajar de peso": "commercial", "obesidad tratamiento": "commercial",
    "inyecciones adelgazar": "commercial",
    "tratamiento obesidad sin cirugia": "commercial",
    "nutriologa en linea": "commercial",
}

VARIANT_MAP = {
    "dieta para diabeticos": "guide",
    "plan alimenticio diabetes": "guide",
    "tratamiento obesidad sin cirugia": "guide",
    "habitos diabetes": "guide",
}


def request_with_retry(pytrends, keywords, geo="MX", max_retries=3):
    """Hace el request con reintentos y backoff exponencial."""
    for attempt in range(max_retries):
        try:
            pytrends.build_payload(keywords, timeframe="today 1-m", geo=geo)
            data = pytrends.interest_over_time()
            return data
        except Exception as e:
            if "429" in str(e):
                wait = (2 ** attempt) * 30 + random.randint(5, 15)
                print(f"  Rate limit. Esperando {wait}s antes de reintentar...")
                time.sleep(wait)
            else:
                print(f"  Error: {e}")
                return None
    return None


def get_trend_scores(pytrends, keywords, geo="MX"):
    """Obtiene scores de tendencia de 1 keyword a la vez para evitar bloqueos."""
    scores = {}
    for kw in keywords:
        data = request_with_retry(pytrends, [kw], geo=geo)
        if data is not None and not data.empty and kw in data.columns:
            scores[kw] = int(data[kw].mean())
        else:
            scores[kw] = 0
        # Pausa aleatoria entre requests para parecer más humano
        time.sleep(random.uniform(6, 10))
    return scores


def get_rising_queries(pytrends, seed_keyword, geo="MX"):
    """Obtiene búsquedas relacionadas en alza."""
    try:
        data = request_with_retry(pytrends, [seed_keyword], geo=geo)
        if data is None:
            return []
        related = pytrends.related_queries()
        if seed_keyword not in related:
            return []
        rising = related[seed_keyword].get("rising")
        if rising is None or rising.empty:
            return []
        return rising.head(5).to_dict("records")
    except Exception as e:
        print(f"  No se pudieron obtener queries relacionadas para '{seed_keyword}': {e}")
        return []


def scan_trends(topics=None, geo="MX", top_n=10):
    print(f"\n🔍 Escaneando Google Trends ({geo}) — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    print("⚠️  Modo lento activado para evitar bloqueos. Esto tarda ~5 minutos.\n")

    pytrends = TrendReq(hl="es-MX", tz=360)
    universe = {k: v for k, v in KEYWORD_UNIVERSE.items()
                if topics is None or k in topics}

    all_results = []

    for i, (topic, keywords) in enumerate(universe.items()):
        if i > 0:
            print(f"  ⏳ Pausa entre pilares (30s)...")
            time.sleep(30)

        print(f"📊 Pilar: {topic} ({len(keywords)} keywords)...")
        scores = get_trend_scores(pytrends, keywords, geo=geo)
        active = sum(1 for s in scores.values() if s > 0)

        for kw, score in scores.items():
            if score > 0:
                all_results.append({
                    "keyword":        kw,
                    "topic":          topic,
                    "trend_score":    score,
                    "intent":         INTENT_MAP.get(kw, "informational"),
                    "variant":        VARIANT_MAP.get(kw, "article"),
                    "extra_tags":     [topic, "trending"],
                })

        print(f"  ✅ {active} keywords con actividad\n")

    # Buscar keywords en alza solo si no hubo bloqueos
    if all_results:
        print("🚀 Buscando keywords en alza...")
        time.sleep(20)
        for seed in ["diabetes tipo 2", "ozempic"]:
            rising = get_rising_queries(pytrends, seed, geo=geo)
            for r in rising:
                query = r.get("query", "").lower()
                if query and len(query) > 5:
                    all_results.append({
                        "keyword":     query,
                        "topic":       _infer_topic(query),
                        "trend_score": min(100, int(r.get("value", 50))),
                        "intent":      _infer_intent(query),
                        "variant":     "article",
                        "extra_tags":  ["trending", "rising"],
                    })
            time.sleep(random.uniform(8, 12))

    # Ordenar y deduplicar
    seen = set()
    deduped = []
    for item in sorted(all_results, key=lambda x: x["trend_score"], reverse=True):
        key = item["keyword"].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:top_n]


def _infer_topic(query):
    q = query.lower()
    if any(w in q for w in ["glucos", "diabet", "insulina", "metformin", "semaglut", "tirzep"]):
        return "glucosa"
    if any(w in q for w in ["peso", "obesi", "adelgaz", "bajar", "grasa"]):
        return "peso"
    if any(w in q for w in ["dieta", "alimento", "comer", "nutri"]):
        return "meal-plan"
    return "journey"


def _infer_intent(query):
    q = query.lower()
    if any(w in q for w in ["precio", "costo", "comprar", "donde"]):
        return "transactional"
    if any(w in q for w in ["clinica", "medico", "tratamiento"]):
        return "commercial"
    return "informational"


def main():
    parser = argparse.ArgumentParser(description="Escanea Google Trends para Clivi SEO")
    parser.add_argument("--topic", help="glucosa, peso, meal-plan, journey")
    parser.add_argument("--top", type=int, default=10, help="Top N keywords (default: 10)")
    parser.add_argument("--output", default="trends_batch.json", help="Archivo de salida")
    parser.add_argument("--geo", default="MX", help="País (default: MX)")
    args = parser.parse_args()

    topics = [args.topic] if args.topic else None
    results = scan_trends(topics=topics, geo=args.geo, top_n=args.top)

    if not results:
        print("⚠️  No se encontraron keywords. Intenta en 15-20 minutos.")
        return

    print(f"\n{'='*55}")
    print(f"TOP {len(results)} KEYWORDS POR TREND SCORE")
    print(f"{'='*55}")
    for i, r in enumerate(results, 1):
        print(f"{i:2}. [{r['trend_score']:3}/100] [{r['topic']:10}] {r['keyword']}")

    payload = {"keywords": [{
        "keyword":        r["keyword"],
        "intent":         r["intent"],
        "topic":          r["topic"],
        "variant":        r["variant"],
        "extra_tags":     r.get("extra_tags", []),
    } for r in results]}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Guardado: {args.output}")
    print(f"\n📤 Para generar artículos:")
    print(f"   curl -X POST http://127.0.0.1:8787/local-test-secret-123/generate \\")
    print(f"     -H \"Content-Type: application/json\" \\")
    print(f"     -d @{args.output}")


if __name__ == "__main__":
    main()