import httpx
from bs4 import BeautifulSoup
import asyncio
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


def limpiar_precio(texto: str) -> float | None:
    """Extrae número de un string tipo '$1.299.990' o '1299990'"""
    if not texto:
        return None
    limpio = re.sub(r"[^\d]", "", texto)
    return float(limpio) if limpio else None


async def scrape_fravega(query: str, client: httpx.AsyncClient) -> dict | None:
    try:
        url = f"https://www.fravega.com/l/?keyword={query.replace(' ', '+')}"
        r = await client.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")

        item = soup.select_one("article")
        if not item:
            return None

        nombre_el = item.select_one("[class*='title'], [class*='Title'], h2, h3")
        precio_el = item.select_one("[class*='price'], [class*='Price']")
        link_el = item.select_one("a[href]")

        nombre = nombre_el.get_text(strip=True) if nombre_el else query
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = link_el["href"] if link_el else None
        url_prod = f"https://www.fravega.com{href}" if href and href.startswith("/") else href

        if not precio:
            return None

        return {
            "tienda": "Fravega",
            "nombre": nombre[:80],
            "precio_contado": precio,
            "precio_cuotas": None,
            "url": url_prod,
        }
    except Exception as e:
        print(f"[Fravega] Error: {e}")
        return None


async def scrape_garbarino(query: str, client: httpx.AsyncClient) -> dict | None:
    try:
        url = f"https://www.garbarino.com/search?q={query.replace(' ', '+')}"
        r = await client.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")

        item = soup.select_one("[class*='product'], [class*='Product']")
        if not item:
            return None

        nombre_el = item.select_one("[class*='title'], [class*='Title'], [class*='name'], h2, h3")
        precio_el = item.select_one("[class*='price'], [class*='Price'], [class*='cash']")
        link_el = item.select_one("a[href]")

        nombre = nombre_el.get_text(strip=True) if nombre_el else query
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None
        href = link_el["href"] if link_el else None
        url_prod = f"https://www.garbarino.com{href}" if href and href.startswith("/") else href

        if not precio:
            return None

        return {
            "tienda": "Garbarino",
            "nombre": nombre[:80],
            "precio_contado": precio,
            "precio_cuotas": None,
            "url": url_prod,
        }
    except Exception as e:
        print(f"[Garbarino] Error: {e}")
        return None


async def scrape_megatone(query: str, client: httpx.AsyncClient) -> dict | None:
    try:
        url = f"https://www.megatone.net/Search.aspx?query={query.replace(' ', '+')}"
        r = await client.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")

        item = soup.select_one(".producto, .product-item, [class*='product']")
        if not item:
            return None

        nombre_el = item.select_one("[class*='title'], [class*='name'], h2, h3, a")
        precio_el = item.select_one("[class*='precio'], [class*='price'], [class*='Price']")

        nombre = nombre_el.get_text(strip=True) if nombre_el else query
        precio = limpiar_precio(precio_el.get_text(strip=True)) if precio_el else None

        if not precio:
            return None

        return {
            "tienda": "Megatone",
            "nombre": nombre[:80],
            "precio_contado": precio,
            "precio_cuotas": None,
            "url": url,
        }
    except Exception as e:
        print(f"[Megatone] Error: {e}")
        return None


async def buscar_en_tiendas(query: str) -> list:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resultados = await asyncio.gather(
            scrape_fravega(query, client),
            scrape_garbarino(query, client),
            scrape_megatone(query, client),
            return_exceptions=True
        )
    return [r for r in resultados if r and not isinstance(r, Exception)]
