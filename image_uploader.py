"""
image_uploader.py
=================
Sube imágenes a Emdash y las asigna automáticamente a los artículos
según su topic.

Flujo:
1. Lee los artículos en borrador que no tienen hero_image
2. Por cada artículo, elige una imagen aleatoria de la carpeta del topic
3. Sube la imagen a Emdash media API
4. Hace PATCH al artículo con el hero_image

Estructura de carpetas:
    IMAGES_DIR/
    ├── glucosa/     → artículos de Diabetes
    ├── peso/        → artículos de Peso
    ├── meal-plan/   → artículos de Nutrición
    └── journey/     → artículos de Movimiento

Uso:
    python image_uploader.py
    python image_uploader.py --dry-run     # ver qué haría sin ejecutar
    python image_uploader.py --topic glucosa  # solo un topic

Requiere:
    pip install requests
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: instala requests con: pip install requests")
    sys.exit(1)

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
# Cambia IMAGES_DIR a la carpeta donde tienes las imágenes
IMAGES_DIR = Path(r"C:\Users\lap\Downloads\CLIVI\Blog\Imagenes")

EMDASH_BASE_URL = "https://clivi-blog-staging.santiago-arboleda.workers.dev"
EMDASH_TOKEN    = "ec_pat_bR3tjVtM6nAOKF0Ap160he33Cz06vHxHBbb8TKX3lXw"

# Extensiones de imagen aceptadas
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Topics disponibles
VALID_TOPICS = {"glucosa", "peso", "meal-plan", "journey"}

# Mapeo de topic slug → nombre de carpeta
TOPIC_TO_FOLDER = {
    "glucosa":   "Diabetes",
    "peso":      "Peso",
    "meal-plan": "Nutrición",
    "journey":   "Movimiento",
}

# ─── FUNCIONES ────────────────────────────────────────────────────────────────

def get_headers():
    return {"Authorization": f"Bearer {EMDASH_TOKEN}"}


def get_drafts_without_image(topic_filter=None):
    """Obtiene artículos en borrador sin hero_image."""
    url = f"{EMDASH_BASE_URL}/_emdash/api/content/posts"
    params = {"status": "draft", "limit": 100}
    
    try:
        res = requests.get(url, headers=get_headers(), params=params)
        if not res.ok:
            print(f"Error obteniendo posts: {res.status_code} {res.text[:200]}")
            return []
        
        data = res.json()
        posts = data.get("data", {}).get("items", []) or data.get("entries", []) or []
        
        results = []
        for post in posts:
            post_data = post.get("data", {})
            hero = post_data.get("hero_image")
            
            # Skip si ya tiene imagen
            if hero and hero.get("src"):
                continue
            
            # Obtener topic via taxonomías
            post_id = post.get("id", "")
            topic = get_post_topic(post_id)
            
            if topic_filter and topic != topic_filter:
                continue
                
            if topic not in VALID_TOPICS:
                continue
                
            results.append({
                "id":    post_id,
                "slug":  post.get("slug", ""),
                "title": post_data.get("title", ""),
                "topic": topic,
            })
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        return []


def get_post_topic(post_id):
    """Intenta obtener el topic de un post."""
    # Buscar en los datos del post directamente
    url = f"{EMDASH_BASE_URL}/_emdash/api/content/posts/{post_id}"
    try:
        res = requests.get(url, headers=get_headers())
        if res.ok:
            data = res.json()
            item = data.get("data", {}).get("item", data.get("data", {}))
            taxonomies = item.get("taxonomies", {})
            topics = taxonomies.get("topic", [])
            if topics:
                return topics[0].get("slug", "") if isinstance(topics[0], dict) else topics[0]
    except:
        pass
    return ""


def get_random_image(topic):
    """Elige una imagen aleatoria de la carpeta del topic."""
    folder = IMAGES_DIR / TOPIC_TO_FOLDER.get(topic, topic)
    
    if not folder.exists():
        print(f"  ⚠️  Carpeta no encontrada: {folder}")
        return None
    
    images = [f for f in folder.iterdir() 
              if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    
    if not images:
        print(f"  ⚠️  No hay imágenes en: {folder}")
        return None
    
    return random.choice(images)


def upload_image(image_path):
    """Sube una imagen a Emdash y devuelve la URL."""
    url = f"{EMDASH_BASE_URL}/_emdash/api/media"
    
    try:
        with open(image_path, "rb") as f:
            res = requests.post(
                url,
                headers=get_headers(),
                files={"file": (image_path.name, f, "image/jpeg")},
            )
        
        if not res.ok:
            print(f"  ❌ Error subiendo imagen: {res.status_code} {res.text[:200]}")
            return None
        
        data = res.json()
        item = data.get("data", {}).get("item", {})
        media_url = item.get("url", "")
        media_id  = item.get("id", "")
        
        if not media_url:
            print(f"  ❌ No se obtuvo URL de la imagen")
            return None
        
        # Convertir URL relativa a absoluta
        if media_url.startswith("/"):
            media_url = f"{EMDASH_BASE_URL}{media_url}"
        
        return {"url": media_url, "id": media_id, "alt": image_path.stem.replace("-", " ")}
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def assign_image_to_post(post_id, media_info, alt_text=""):
    """Asigna el hero_image a un artículo via PATCH."""
    url = f"{EMDASH_BASE_URL}/_emdash/api/content/posts/{post_id}"
    
    payload = {
        "data": {
            "hero_image": {
                "src": media_info["url"],
                "alt": alt_text or media_info.get("alt", ""),
            }
        }
    }
    
    try:
        res = requests.patch(
            url,
            headers={**get_headers(), "Content-Type": "application/json"},
            json=payload,
        )
        return res.ok, res.status_code
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Sube imágenes a artículos de Emdash")
    parser.add_argument("--topic",   help="Solo procesar un topic: glucosa, peso, meal-plan, journey")
    parser.add_argument("--dry-run", action="store_true", help="Ver qué haría sin ejecutar")
    parser.add_argument("--token",   help="Token de API de Emdash (override)")
    parser.add_argument("--url",     help="URL base de Emdash (override)")
    parser.add_argument("--images",  help="Carpeta de imágenes (override)")
    args = parser.parse_args()

    global EMDASH_TOKEN, EMDASH_BASE_URL, IMAGES_DIR
    if args.token:  EMDASH_TOKEN    = args.token
    if args.url:    EMDASH_BASE_URL = args.url.rstrip("/")
    if args.images: IMAGES_DIR      = Path(args.images)

    print(f"\n🖼️  Image Uploader — Clivi Blog")
    print(f"   Base URL:  {EMDASH_BASE_URL}")
    print(f"   Imágenes:  {IMAGES_DIR}")
    if args.dry_run:
        print("   Modo:      DRY RUN (no ejecuta cambios)\n")
    else:
        print()

    # Verificar carpeta de imágenes
    if not IMAGES_DIR.exists():
        print(f"❌ La carpeta de imágenes no existe: {IMAGES_DIR}")
        print(f"   Créala con subcarpetas: glucosa/, peso/, meal-plan/, journey/")
        sys.exit(1)

    # Obtener artículos sin imagen
    print("🔍 Buscando artículos sin imagen...")
    posts = get_drafts_without_image(args.topic)

    if not posts:
        print("✅ Todos los artículos ya tienen imagen o no hay borradores.")
        return

    print(f"   Encontrados: {len(posts)} artículos sin imagen\n")

    success = 0
    errors  = 0

    for post in posts:
        print(f"📄 [{post['topic']:10}] {post['title'][:55]}")
        
        # Elegir imagen aleatoria
        image_path = get_random_image(post["topic"])
        if not image_path:
            errors += 1
            continue
        
        print(f"   🖼️  Imagen: {image_path.name}")
        
        if args.dry_run:
            print(f"   ✓  [DRY RUN] Se asignaría {image_path.name}")
            success += 1
            continue
        
        # Subir imagen
        media_info = upload_image(image_path)
        if not media_info:
            errors += 1
            continue
        
        # Asignar al artículo
        ok, status = assign_image_to_post(post["id"], media_info, post["title"])
        if ok:
            print(f"   ✅ Asignada: {media_info['url'].split('/')[-1]}")
            success += 1
        else:
            print(f"   ⚠️  PATCH falló ({status}) — imagen subida pero no asignada")
            print(f"      URL de imagen: {media_info['url']}")
            errors += 1

    print(f"\n{'='*50}")
    print(f"✅ Exitosos: {success}")
    if errors:
        print(f"❌ Errores:  {errors}")
    print()


if __name__ == "__main__":
    main()
