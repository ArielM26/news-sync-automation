import requests
import base64
import json
import time
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime
import re

class PuraNoticiaExtractor:
    def __init__(self):
        self.base_url = "https://puranoticia.pnt.cl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Configuración de categorías
        self.categories = {
            'Nacional': 'https://puranoticia.pnt.cl/tax/nacional/p/1',
            'Regiones': 'https://puranoticia.pnt.cl/cms/site/tax/port/fid_noticia/embed_1___1.html',
            'Deportes': 'https://puranoticia.pnt.cl/cms/site/tax/port/fid_noticia/embed_10___1.html',
            'Internacional': 'https://puranoticia.pnt.cl/cms/site/tax/port/fid_noticia/embed_3___1.html',
            'Región de Valparaíso': 'https://puranoticia.pnt.cl/cms/site/tax/port/fid_noticia/embed_14___1.html',
            'Espectáculos': 'https://puranoticia.pnt.cl/cms/site/tax/port/fid_noticia/embed_11___1.html',
            'Negocios': 'https://puranoticia.pnt.cl/cms/site/tax/port/fid_noticia/embed_4___1.html'
        }

    def extract_first_news_url(self, category_url):
        """Extrae la URL de la primera noticia de una página de categoría"""
        try:
            response = self.session.get(category_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Buscar el primer enlace válido de noticia
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href')
                if href and self.is_valid_news_url(href):
                    if href.startswith('/'):
                        return self.base_url + href
                    elif href.startswith('http'):
                        return href

            return None

        except Exception as e:
            print(f"❌ Error extrayendo URL de {category_url}: {e}")
            return None

    def is_valid_news_url(self, url):
        """Valida si una URL es de una noticia válida"""
        exclude_patterns = [
            'embed_', 'javascript:', '#', 'mailto:', 'tel:', '/cms/imag/',
            '.jpg', '.png', '.gif', '.webp', '.pdf', '.doc', '.xlsx',
            'facebook.com', 'twitter.com', 'instagram.com', 'whatsapp.com',
            'linkedin.com', '/tax/', '/cms/site/tax/'
        ]

        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False

        # Debe ser una URL interna significativa
        if url.startswith('/') and len(url) > 15:
            return True
        elif 'puranoticia.pnt.cl' in url and len(url) > 50:
            return True

        return False

    def extract_article_content(self, url):
        """Extrae el contenido completo de un artículo"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extraer título
            title = self.extract_title(soup)

            # Extraer subtítulo
            subtitle = self.extract_subtitle(soup)

            # Extraer imagen principal
            main_image = self.extract_main_image(soup)

            # Extraer fecha y hora
            date_time = self.extract_date_time(soup)

            # Extraer contenido
            content = self.extract_content(soup)

            return {
                'title': title,
                'subtitle': subtitle,
                'main_image': main_image,
                'date_time': date_time,
                'content': content,
                'url': url
            }

        except Exception as e:
            print(f"❌ Error extrayendo contenido de {url}: {e}")
            return None

    def extract_title(self, soup):
        """Extrae el título del artículo"""
        try:
            # Método 1: buscar en contenido-ppal
            contenido_ppal = soup.find(id='contenido-ppal')
            if contenido_ppal:
                h1 = contenido_ppal.find('h1')
                if h1:
                    return h1.get_text(strip=True)

            # Método 2: buscar H1 general
            h1 = soup.find('h1')
            if h1:
                return h1.get_text(strip=True)

            # Método 3: buscar en title
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text(strip=True)

        except Exception:
            pass
        return ""

    def extract_subtitle(self, soup):
        """Extrae el subtítulo del artículo"""
        try:
            bajada = soup.find('p', class_='bajada')
            if bajada:
                return bajada.get_text(strip=True)
        except Exception:
            pass
        return ""

    def extract_main_image(self, soup):
        """Extrae la imagen principal del artículo"""
        try:
            # Método 1: buscar en figure con clase específica
            figure = soup.find('figure', class_='img-wrap desktop')
            if figure:
                img = figure.find('img')
                if img and img.get('src'):
                    src = img.get('src')
                    if src.startswith('/'):
                        return self.base_url + src
                    return src

            # Método 2: buscar primera imagen en el contenido
            cuerpo = soup.find('div', class_='CUERPO')
            if cuerpo:
                img = cuerpo.find('img')
                if img and img.get('src'):
                    src = img.get('src')
                    if src.startswith('/'):
                        return self.base_url + src
                    return src

        except Exception:
            pass
        return ""

    def extract_date_time(self, soup):
        """Extrae la fecha y hora del artículo"""
        try:
            # Buscar en div con clase date
            date_div = soup.find('div', class_='date')
            if date_div:
                full_text = date_div.get_text(strip=True)

                # Buscar span con hora
                time_span = date_div.find('span')
                if time_span:
                    time_text = time_span.get_text(strip=True)
                    date_text = full_text.replace(time_text, "").strip()
                    return {
                        'date': date_text,
                        'time': time_text,
                        'full': full_text
                    }

                # Si no hay span, buscar patrón de hora
                time_match = re.search(r'(\d{1,2}:\d{2})', full_text)
                if time_match:
                    time_text = time_match.group(1)
                    date_text = full_text.replace(time_text, "").strip()
                    return {
                        'date': date_text,
                        'time': time_text,
                        'full': full_text
                    }

                return {
                    'date': full_text,
                    'time': '',
                    'full': full_text
                }

        except Exception:
            pass

        # Fecha actual como fallback
        now = datetime.now()
        return {
            'date': now.strftime('%A %d de %B de %Y'),
            'time': now.strftime('%H:%M'),
            'full': now.strftime('%A %d de %B de %Y %H:%M')
        }

    def extract_content(self, soup):
        """Extrae el contenido del artículo"""
        try:
            cuerpo_div = soup.find('div', class_='CUERPO')
            if cuerpo_div:
                # Limpiar elementos no deseados
                for selector in [
                    'div.ad-pnt-slot',
                    'div.subtitulos',
                    'div.anclas',
                    'div.banner-plain'
                ]:
                    for element in cuerpo_div.select(selector):
                        element.decompose()

                # Eliminar blockquotes con "LEER TAMBIÉN"
                for blockquote in cuerpo_div.find_all('blockquote'):
                    text = blockquote.get_text().strip().upper()
                    if 'LEER TAMBIÉN' in text or 'LEER TAMBIEN' in text:
                        blockquote.decompose()

                # Convertir rutas relativas de imágenes a absolutas
                for img in cuerpo_div.find_all('img'):
                    src = img.get('src')
                    if src and src.startswith('/'):
                        img['src'] = self.base_url + src

                return str(cuerpo_div)

        except Exception:
            pass
        return ""

    def extract_latest_news(self):
        """Extrae la primera noticia de cada categoría"""
        print("🔍 Iniciando extracción de noticias de Pura Noticia...")

        extracted_news = []

        for category_name, category_url in self.categories.items():
            print(f"📰 Procesando categoría: {category_name}")

            # Extraer URL de la primera noticia
            first_news_url = self.extract_first_news_url(category_url)

            if first_news_url:
                print(f"   ✓ URL encontrada: {first_news_url[:60]}...")

                # Extraer contenido completo
                article_data = self.extract_article_content(first_news_url)

                if article_data and article_data['title']:
                    article_data['category'] = category_name
                    extracted_news.append(article_data)
                    print(f"   ✓ Extraído: {article_data['title'][:50]}...")
                else:
                    print(f"   ✗ Error extrayendo contenido")
            else:
                print(f"   ✗ No se encontró URL válida")

            time.sleep(0.5)  # Pausa entre requests

        print(f"✅ Extracción completada: {len(extracted_news)} noticias extraídas")
        return extracted_news

class WordPressAPI:
    def __init__(self, site_url, username, app_password):
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.app_password = app_password

        # Crear credenciales de autenticación
        credentials = f"{username}:{app_password}"
        self.token = base64.b64encode(credentials.encode()).decode()

        self.headers = {
            'Authorization': f'Basic {self.token}',
            'Content-Type': 'application/json'
        }

        # Cache para IDs de categorías
        self.category_cache = {}

    def test_connection(self):
        """Prueba la conexión con WordPress"""
        try:
            api_url = f"{self.site_url}/wp-json/wp/v2/users/me"
            response = requests.get(api_url, headers=self.headers)

            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Conexión exitosa con WordPress")
                print(f"   Usuario: {user_data.get('name', 'N/A')}")
                return True
            else:
                print(f"❌ Error de conexión: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False

    def get_category_id(self, category_name):
        """Obtiene el ID de una categoría por nombre"""
        if category_name in self.category_cache:
            return self.category_cache[category_name]

        try:
            api_url = f"{self.site_url}/wp-json/wp/v2/categories"
            params = {'search': category_name, 'per_page': 10}
            response = requests.get(api_url, headers=self.headers, params=params)

            if response.status_code == 200:
                categories = response.json()
                for category in categories:
                    if category['name'].lower() == category_name.lower():
                        self.category_cache[category_name] = category['id']
                        return category['id']

            print(f"⚠️ Categoría '{category_name}' no encontrada")
            return None

        except Exception as e:
            print(f"❌ Error obteniendo categoría '{category_name}': {e}")
            return None

    def get_recent_posts_by_category(self, category_name, limit=5):
        """Obtiene los posts recientes de una categoría"""
        try:
            category_id = self.get_category_id(category_name)
            if not category_id:
                return []

            api_url = f"{self.site_url}/wp-json/wp/v2/posts"
            params = {
                'categories': category_id,
                'per_page': limit,
                'orderby': 'date',
                'order': 'desc'
            }

            response = requests.get(api_url, headers=self.headers, params=params)

            if response.status_code == 200:
                posts = response.json()
                return [{'title': post['title']['rendered'], 'id': post['id']} for post in posts]
            else:
                print(f"❌ Error obteniendo posts de '{category_name}': {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error obteniendo posts de '{category_name}': {e}")
            return []

    def post_exists(self, title, category_name):
        """Verifica si un post ya existe por título exacto"""
        recent_posts = self.get_recent_posts_by_category(category_name, 5)

        for post in recent_posts:
            if post['title'].strip() == title.strip():
                return True

        return False

    def upload_image(self, image_url, filename):
        """Sube una imagen a WordPress y retorna el ID del attachment"""
        try:
            # Descargar la imagen
            print(f"   📥 Descargando imagen: {image_url[:50]}...")
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()

            # Determinar tipo de contenido
            content_type = img_response.headers.get('content-type', 'image/jpeg')

            # Preparar datos para upload
            files = {
                'file': (filename, img_response.content, content_type)
            }

            # Headers para upload (sin Content-Type para multipart)
            upload_headers = {
                'Authorization': f'Basic {self.token}'
            }

            # Subir imagen a WordPress
            api_url = f"{self.site_url}/wp-json/wp/v2/media"
            upload_response = requests.post(api_url, headers=upload_headers, files=files)

            if upload_response.status_code == 201:
                media_data = upload_response.json()
                print(f"   ✅ Imagen subida exitosamente (ID: {media_data['id']})")
                return media_data['id']
            else:
                print(f"   ❌ Error subiendo imagen: {upload_response.status_code}")
                return None

        except Exception as e:
            print(f"   ❌ Error procesando imagen: {e}")
            return None

    def create_post(self, article_data):
        """Crea un nuevo post en WordPress con imagen destacada"""
        try:
            category_id = self.get_category_id(article_data['category'])
            if not category_id:
                print(f"❌ No se pudo obtener ID de categoría '{article_data['category']}'")
                return False

            # Subir imagen destacada si existe
            featured_image_id = None
            if article_data['main_image']:
                print(f"   🖼️ Procesando imagen destacada...")

                # Generar nombre de archivo único
                parsed_url = urlparse(article_data['main_image'])
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"imagen_{int(time.time())}.jpg"

                featured_image_id = self.upload_image(article_data['main_image'], filename)

            # Preparar datos del post
            post_data = {
                'title': article_data['title'],
                'content': article_data['content'],
                'excerpt': article_data['subtitle'],
                'status': 'publish',
                'categories': [category_id],
                'meta': {
                    'pura_noticia_url': article_data['url']
                }
            }

            # Agregar imagen destacada si se subió exitosamente
            if featured_image_id:
                post_data['featured_media'] = featured_image_id
                print(f"   🎯 Imagen destacada asignada (ID: {featured_image_id})")

            # Crear el post
            api_url = f"{self.site_url}/wp-json/wp/v2/posts"
            response = requests.post(api_url, headers=self.headers, json=post_data)

            if response.status_code == 201:
                post = response.json()
                print(f"✅ Post creado: {post['title']['rendered']}")
                print(f"   URL: {post['link']}")
                if featured_image_id:
                    print(f"   🖼️ Con imagen destacada")
                return True
            else:
                print(f"❌ Error creando post: {response.status_code}")
                print(f"   Respuesta: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"❌ Error creando post: {e}")
            return False

def run_news_sync():
    """Función principal para ejecutar la sincronización"""
    print("🚀 SINCRONIZADOR DE NOTICIAS: Pura Noticia → 247 Noticias")
    print("=" * 60)

    # Configuración de WordPress
    WORDPRESS_CONFIG = {
        'site_url': 'https://247noticias.cl',
        'username': 'ameneses',
        'app_password': 'Z7Rc 8Yca eN0s vKnc 5Ler C3zT'
    }

    try:
        # PASO 1: Probar conexión con WordPress
        print("🔐 PASO 1: Probando conexión con WordPress...")
        wordpress_api = WordPressAPI(
            WORDPRESS_CONFIG['site_url'],
            WORDPRESS_CONFIG['username'],
            WORDPRESS_CONFIG['app_password']
        )

        if not wordpress_api.test_connection():
            print("❌ No se pudo conectar con WordPress. Verifica las credenciales.")
            return

        # PASO 2: Extraer noticias de Pura Noticia
        print("\n📰 PASO 2: Extrayendo noticias de Pura Noticia...")
        extractor = PuraNoticiaExtractor()
        extracted_news = extractor.extract_latest_news()

        if not extracted_news:
            print("⚠️ No se extrajeron noticias. Terminando proceso.")
            return

        # PASO 3: Verificar existencia en WordPress
        print(f"\n🔍 PASO 3: Verificando existencia en WordPress...")
        news_to_create = []
        existing_count = 0

        for news in extracted_news:
            if wordpress_api.post_exists(news['title'], news['category']):
                existing_count += 1
                print(f"   ⚠️ Ya existe: {news['title'][:50]}...")
            else:
                news_to_create.append(news)
                print(f"   ✅ Nuevo: {news['title'][:50]}...")

        # PASO 4: Crear nuevas noticias
        if news_to_create:
            print(f"\n📝 PASO 4: Creando {len(news_to_create)} nuevas noticias...")
            created_count = 0
            error_count = 0

            for i, news in enumerate(news_to_create):
                print(f"\n   🔄 Creando {i+1}/{len(news_to_create)}: {news['title'][:50]}...")

                if wordpress_api.create_post(news):
                    created_count += 1
                else:
                    error_count += 1

                time.sleep(2)  # Pausa entre creaciones para no sobrecargar
        else:
            print(f"\nℹ️ No hay noticias nuevas para crear.")
            created_count = 0
            error_count = 0

        # RESUMEN FINAL
        print("\n" + "=" * 60)
        print("🎉 SINCRONIZACIÓN COMPLETADA")
        print("=" * 60)
        print(f"📊 ESTADÍSTICAS FINALES:")
        print(f"   • Noticias extraídas: {len(extracted_news)}")
        print(f"   • Ya existentes: {existing_count}")
        print(f"   • Nuevas creadas: {created_count}")
        print(f"   • Errores: {error_count}")
        print("=" * 60)

        if created_count > 0:
            print(f"✅ ¡Éxito! Se crearon {created_count} noticias nuevas en WordPress.")
        else:
            print("ℹ️ No había noticias nuevas para crear. Todas ya existían.")

    except Exception as e:
        print(f"❌ Error crítico: {e}")

# =========================================
# EJECUCIÓN PRINCIPAL
# =========================================

if __name__ == "__main__":
    # Solo ejecutar si quieres probar inmediatamente
    # Puedes comentar esta línea y ejecutar manualmente con: run_news_sync()

    print("📋 Código cargado correctamente.")
    print("🚀 Para ejecutar la sincronización, ejecuta: run_news_sync()")
    print("\n💡 O ejecuta directamente:")

    # Ejecutar automáticamente (descomenta la siguiente línea)
    run_news_sync()
