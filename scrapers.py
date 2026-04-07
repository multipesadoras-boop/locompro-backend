import httpx
from bs4 import BeautifulSoup
import asyncio
import re
import urllib.parse

# Headers globales simulando un navegador móvil moderno para evitar bloqueos básicos
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def limpiar_precio(texto: str) -> float | None:
    """
    Extrae un número flotante de un string de precio argentino.
    Maneja formatos como: '$1.299.990,50', '1299990.50', '1.299.990'
    """
    if not texto:
        return None
    # Elimina todo lo que no sea dígito, coma o punto
    limpio = re.sub(r"[^\d,.]", "", texto)
    if not limpio:
        return None

    # Determina si el último separador es una coma (formato ES) o punto (formato EN)
    marcador_decimal_coma = limpio.rfind(',') > limpio.rfind('.')
    
    if marcador_decimal_coma:
        # Formato 1.234,56 -> 1234.56
        limpio = limpio.replace('.', '').replace(',', '.')
    else:
        # Formato 1,234.56 o 1234.56 -> 1234.56
        limpio = limpio.replace(',', '')
        
    try:
        return float(limpio)
    except ValueError:
        return None


# --- Funciones de Scraping Individuales ---

async def fetch_api_or_html(url: str, client: httpx.AsyncClient, label: str):
    """Función auxiliar para realizar la petición con manejo de errores básico."""
    try:
        r = await client.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status() # Lanza excepción si hay error HTTP (404, 500, etc.)
        return r
    except httpx.RequestError as e:
        print(f"[{label}] Error de conexión: {e}")
    except httpx.HTTPStatusError as e:
        print(f"[{label}] Error HTTP {e.response.status_code}: {e}")
    except Exception as e:
        print(f"[{label}] Error inesperado: {e}")
    return None

def armar_resultado(tienda, nombre, precio, url) -> dict | None:
    """Estructura el diccionario de resultado de forma consistente."""
    if not precio: return None
    return {
        "tienda": tienda,
        "nombre": nombre[:90].strip() if nombre else "Producto",
        "precio_contado": precio,
        "url": url,
    }


async def scrape_mercado_libre(query: str, client: httpx.AsyncClient) -> dict | None:
    # Mercado Libre tiene una estructura HTML muy estable.
    tienda = "Mercado Libre"
    url = f"https://listado.mercadolibre.com.ar/{query.replace(' ', '-')}_NoIndex_True#D[A:{query.replace(' ', '%20')},on]"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Busca el primer ítem de resultado
    item = soup.select_one(".ui-search-result__content-wrapper, .ui-search-layout__item")
    if not item: return None
    
    try:
        nombre = item.select_one(".ui-search-item__title").get_text(strip=True)
        # ML separa la parte entera de la decimal en diferentes spans
        pre_entero = item.select_one(".ui-search-price__part--number").get_text(strip=True)
        pre_decimal = item.select_one(".ui-search-price__part--decimal")
        
        texto_precio = pre_entero
        if pre_decimal:
            texto_precio += "," + pre_decimal.get_text(strip=True)
            
        precio = limpiar_precio(texto_precio)
        href = item.select_one(".ui-search-link")["href"]
        
        return armar_resultado(tienda, nombre, precio, href)
    except: return None


async def scrape_fravega(query: str, client: httpx.AsyncClient) -> dict | None:
    # Se mantienen los selectores originales actualizados
    tienda = "Fravega"
    url = f"https://www.fravega.com/l/?keyword={urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one("article[itemtype='http://schema.org/Product']")
    if not item: return None

    try:
        nombre = item.select_one("span[class*='ProductTitle']").get_text(strip=True)
        precio_el = item.select_one("span[class*='PriceBarSalePrice']")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a")["href"]
        url_prod = f"https://www.fravega.com{href}" if href.startswith("/") else href
        
        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


async def scrape_oncity(query: str, client: httpx.AsyncClient) -> dict | None:
    # OnCity usa VTEX, buscamos clases típicas de esta plataforma
    tienda = "OnCity"
    url = f"https://www.oncity.com.ar/{urllib.parse.quote(query)}?_q={urllib.parse.quote(query)}&map=ft"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".vtex-product-summary-2-x-container, .vtex-search-result-3-x-galleryItem")
    if not item: return None

    try:
        nombre = item.select_one(".vtex-product-summary-2-x-productBrand").get_text(strip=True)
        precio_el = item.select_one(".vtex-product-summary-2-x-currencyContainer")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a.vtex-product-summary-2-x-clearLink")["href"]
        url_prod = f"https://www.oncity.com.ar{href}" if href.startswith("/") else href
        
        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


async def scrape_carrefour(query: str, client: httpx.AsyncClient) -> dict | None:
    # Carrefour también suele usar VTEX o estructuras similares
    tienda = "Carrefour"
    url = f"https://www.carrefour.com.ar/busqueda/{urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".vtex-search-result-3-x-galleryItem, [class*='productSummaryContainer']")
    if not item: return None

    try:
        nombre = item.select_one("[class*='productBrand'], .vtex-product-summary-2-x-brandName").get_text(strip=True)
        # Buscamos el precio de venta (sellingPrice)
        precio_el = item.select_one("[class*='sellingPrice']")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a")["href"]
        url_prod = f"https://www.carrefour.com.ar{href}" if href.startswith("/") else href
        
        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


async def scrape_tienda_newsan(query: str, client: httpx.AsyncClient) -> dict | None:
    # Tienda Newsan (Noblex, Atma, Philco, etc.)
    tienda = "Tienda Newsan"
    url = f"https://www.tiendanewsan.com.ar/busqueda/{urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".vtex-search-result-3-x-galleryItem")
    if not item: return None

    try:
        nombre = item.select_one(".vtex-product-summary-2-x-productBrand").get_text(strip=True)
        precio_el = item.select_one(".vtex-product-summary-2-x-price_sellingPrice")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a.vtex-product-summary-2-x-clearLink")["href"]
        url_prod = f"https://www.tiendanewsan.com.ar{href}" if href.startswith("/") else href
        
        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


async def scrape_musimundo(query: str, client: httpx.AsyncClient) -> dict | None:
    tienda = "Musimundo"
    url = f"https://www.musimundo.com/search/?text={urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".product-item, .mus-pro-dd-item")
    if not item: return None

    try:
        nombre = item.select_one(".mus-pro-name, .name").get_text(strip=True)
        precio_el = item.select_one(".mus-pro-price, .price")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a")["href"]
        url_prod = f"https://www.musimundo.com{href}" if href.startswith("/") else href
        
        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


async def scrape_coppel(query: str, client: httpx.AsyncClient) -> dict | None:
    tienda = "Coppel"
    # Coppel usa parámetros de búsqueda estándar en la URL
    url = f"https://www.coppel.com.ar/catalogsearch/result/?q={urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".product-item-info, .productItem")
    if not item: return None

    try:
        nombre = item.select_one(".product-item-name, .productName").get_text(strip=True)
        precio_el = item.select_one(".price-final_price .price, .finalPrice")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a.product-item-link, a")["href"]
        
        return armar_resultado(tienda, nombre, precio, href)
    except: return None


async def scrape_pardo(query: str, client: httpx.AsyncClient) -> dict | None:
    tienda = "Pardo"
    url = f"https://www.pardo.com.ar/catalogsearch/result/?q={urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".product-item-info, .div-product-solr")
    if not item: return None

    try:
        nombre = item.select_one(".product-item-name, .name-product-solr").get_text(strip=True)
        precio_el = item.select_one(".price-final_price .price, .price-product-solr")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a")["href"]
        
        return armar_resultado(tienda, nombre, precio, href)
    except: return None


async def scrape_casa_del_audio(query: str, client: httpx.AsyncClient) -> dict | None:
    tienda = "Casa del Audio"
    url = f"https://www.casadelaudio.com/bps/search?q={urllib.parse.quote(query)}"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")
    
    item = soup.select_one(".product-item, .card-product")
    if not item: return None

    try:
        nombre = item.select_one(".product-item-name, .title").get_text(strip=True)
        precio_el = item.select_one(".price-final_price .price, .price")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a")["href"]
        url_prod = f"https://www.casadelaudio.com{href}" if href.startswith("/") else href
        
        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


async def scrape_megatone(query: str, client: httpx.AsyncClient) -> dict | None:
    # Se mantiene y actualiza Megatone
    tienda = "Megatone"
    url = f"https://www.megatone.net/busqueda/{urllib.parse.quote(query)}/"
    
    response = await fetch_api_or_html(url, client, tienda)
    if not response: return None
    soup = BeautifulSoup(response.text, "html.parser")

    item = soup.select_one(".vtex-search-result-3-x-galleryItem, .product-item")
    if not item: return None

    try:
        nombre = item.select_one(".vtex-product-summary-2-x-productBrand, h3").get_text(strip=True)
        precio_el = item.select_one(".vtex-product-summary-2-x-price_sellingPrice, .price")
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = item.select_one("a")["href"]
        url_prod = f"https://www.megatone.net{href}" if href.startswith("/") else href

        return armar_resultado(tienda, nombre, precio, url_prod)
    except: return None


# --- Función Principal de Búsqueda Asíncrona ---

async def buscar_en_tiendas(query: str) -> list:
    print(f"\nBuscando '{query}' en tiendas de Argentina...")
    
    # Usamos límites de conexión más altos para acelerar la búsqueda paralela
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=20)
    
    async with httpx.AsyncClient(headers=HEADERS, limits=limits, follow_redirects=True, http2=True) as client:
        # Lista de todas las funciones de scraping a ejecutar en paralelo
        tareas = [
            scrape_mercado_libre(query, client),
            scrape_fravega(query, client),
            scrape_oncity(query, client),
            scrape_carrefour(query, client),
            scrape_tienda_newsan(query, client),
            scrape_musimundo(query, client),
            scrape_coppel(query, client),
            scrape_pardo(query, client),
            scrape_casa_del_audio(query, client),
            scrape_megatone(query, client),
        ]
        
        # Ejecuta todas las búsquedas al mismo tiempo
        resultados_raw = await asyncio.gather(*tareas, return_exceptions=True)
    
    # Filtra errores y resultados nulos, y ordena por precio de menor a mayor
    resultados = []
    for r in resultados_raw:
        if r and isinstance(r, dict) and r.get("precio_contado"):
            resultados.append(r)
            
    resultados.sort(key=lambda x: x["precio_contado"])
    return resultados


# --- Ejemplo de Uso ---

if __name__ == "__main__":
    import json
    import time
    
    # Producto a buscar
    producto_buscado = "moto g24 ultra"
    
    start_time = time.time()
    
    # Ejecuta el bucle asíncrono
    try:
        res = asyncio.run(buscar_en_tiendas(producto_buscado))
        
        end_time = time.time()
        
        print(f"\nSe encontraron {len(res)} resultados en {end_time - start_time:.2f} segundos:\n")
        
        # Imprime los resultados en formato JSON legible
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    except KeyboardInterrupt:
        print("\nBúsqueda cancelada por el usuario.")
