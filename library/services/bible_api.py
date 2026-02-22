"""
services/bible_api.py
─────────────────────
Cliente para la API pública de Biblia (https://biblia-api.qhar.in/).

Reina Valera 1909 en formato JSON — no requiere API key.

Responsabilidades:
  - Construir la URL correcta a partir del passage_id.
  - Parsear la respuesta y devolver un dict limpio {texto, referencia}.
  - Manejar errores de red y de formato sin romper la app.
  - Cachear el resultado del día para no llamar a la API en cada request.
"""

import re
import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

# ─── URL base de la API ───────────────────────────────────────────────────────
_BASE_URL = "https://biblia-api.qhar.in"

# ─── Lista de pasajes diarios ─────────────────────────────────────────────────
# Formato: LIBRO.CAPITULO.VERSICULO  o  LIBRO.CAPITULO.VERSICULO_INICIO-FIN
# Se usa el día del año para elegir el versículo de forma determinista.
PASAJES_DIARIOS = [
    "JHN.3.16",       # De tal manera amó Dios al mundo...
    "PSA.23.1-6",     # El Señor es mi pastor...
    "PRO.3.5-6",      # Confía en el Señor con todo tu corazón...
    "PHP.4.13",       # Todo lo puedo en Cristo...
    "ROM.8.28",       # Sabemos que a los que aman a Dios...
    "ISA.40.31",      # Los que esperan en el Señor renovarán sus fuerzas...
    "JER.29.11",      # Porque yo sé los planes que tengo para vosotros...
    "MAT.6.33",       # Mas buscad primeramente el reino de Dios...
    "PSA.46.1",       # Dios es nuestro amparo y fortaleza...
    "PHP.4.6-7",      # Por nada estéis afanosos...
    "ROM.12.2",       # No os conforméis a este siglo...
    "GAL.5.22-23",    # El fruto del Espíritu es amor, gozo, paz...
    "1CO.13.4-7",     # El amor es sufrido, es benigno...
    "PSA.91.1-2",     # El que habita al abrigo del Altísimo...
    "ROM.8.38-39",    # Nada nos podrá separar del amor de Dios...
    "ISA.41.10",      # No temas, porque yo estoy contigo...
    "2TI.1.7",        # No nos ha dado Dios espíritu de cobardía...
    "HEB.11.1",       # La fe es la certeza de lo que se espera...
    "JHN.14.6",       # Yo soy el camino, la verdad y la vida...
    "MAT.11.28-30",   # Venid a mí todos los que estáis cansados...
    "PSA.119.105",    # Lámpara es a mis pies tu palabra...
    "PRO.22.6",       # Instruye al niño en su camino...
    "1JN.4.7-8",      # Amémonos unos a otros, porque el amor es de Dios...
    "PSA.37.4",       # Deléitate asimismo en el Señor...
    "ROM.5.8",        # Dios muestra su amor: siendo aún pecadores...
    "JHN.11.25",      # Yo soy la resurrección y la vida...
    "2CH.7.14",       # Si se humillare mi pueblo...
    "PSA.27.1",       # El Señor es mi luz y mi salvación...
    "ISA.53.5",       # Herido fue por nuestras rebeliones...
    "JHN.10.10",      # Yo he venido para que tengan vida...
    "ROM.1.16",       # No me avergüenzo del evangelio de Cristo...
    "PHP.1.21",       # Para mí el vivir es Cristo...
    "PSA.34.8",       # Gustad y ved que es bueno el Señor...
    "MAT.28.19-20",   # Id y haced discípulos a todas las naciones...
    "2CO.5.17",       # Si alguno está en Cristo, nueva criatura es...
    "EPH.2.8-9",      # Por gracia sois salvos por medio de la fe...
    "JHN.1.1",        # En el principio era el Verbo...
    "GEN.1.1",        # En el principio creó Dios los cielos y la tierra...
    "REV.21.4",       # Enjugará Dios toda lágrima de los ojos de ellos...
    "1PE.5.7",        # Echad toda vuestra ansiedad sobre él...
    "MAT.5.3-5",      # Bienaventurados los pobres en espíritu...
    "ROM.6.23",       # La paga del pecado es muerte, mas la dádiva de Dios...
    "JHN.8.32",       # Conoceréis la verdad, y la verdad os hará libres...
    "PSA.103.1-4",    # Bendice, alma mía, al Señor...
    "PRO.16.9",       # El corazón del hombre piensa su camino...
    "COL.3.23",       # Y todo lo que hagáis, hacedlo de corazón...
    "1CO.10.13",      # No os ha sobrevenido ninguna tentación...
    "LUK.1.37",       # Porque nada hay imposible para Dios...
    "PSA.1.1-3",      # Bienaventurado el varón que no anduvo...
    "PRO.4.23",       # Sobre toda cosa guardada, guarda tu corazón...
    "MAT.5.9",        # Bienaventurados los pacificadores...
    "ACT.1.8",        # Recibiréis poder cuando el Espíritu Santo venga...
    "HEB.4.12",       # La palabra de Dios es viva y eficaz...
]


# ─── Caché en memoria (persiste por proceso, se renueva cada día) ─────────────
_cache: dict = {"fecha": None, "resultado": None}


def _passage_to_url(passage_id: str) -> str | None:
    """
    Convierte un passage_id al path de la API.

    Ejemplos:
        "JHN.3.16"   → "/book/JHN/chapter/3/verse/16"
        "PSA.23.1-6" → "/book/PSA/chapter/23/verse/1-6"
    """
    partes = passage_id.split(".")
    if len(partes) != 3:
        logger.error("passage_id con formato inválido: %s", passage_id)
        return None
    libro, capitulo, versiculo = partes
    return f"/book/{libro}/chapter/{capitulo}/verse/{versiculo}"


def _limpiar_contenido(versos: list) -> tuple[str, str]:
    """
    Recibe la lista de versos de la API y devuelve (texto_limpio, referencia).

    - Elimina marcadores [N] de número de versículo.
    - Une múltiples versos con un espacio.
    - Construye la referencia en formato "Libro Cap:V" o "Libro Cap:V-V".
    """
    textos = []
    for v in versos:
        # Quitar "[N] " al inicio de cada verso
        texto = re.sub(r'\[\d+\]\s*', '', v.get("content", "")).strip()
        textos.append(texto)

    texto_final = " ".join(textos).strip()

    # Referencia: si es rango, añadir el número del último verso
    referencia = versos[0]["reference"]
    if len(versos) > 1:
        referencia = f"{referencia}-{versos[-1]['number']}"

    return texto_final, referencia


def get_pasaje_del_dia() -> str:
    """Devuelve el passage_id del día actual (determinista por fecha)."""
    dia_del_año = date.today().timetuple().tm_yday   # 1 … 365/366
    indice = (dia_del_año - 1) % len(PASAJES_DIARIOS)
    return PASAJES_DIARIOS[indice]


def obtener_versiculo(passage_id: str) -> dict | None:
    """
    Consulta biblia-api.qhar.in y retorna el contenido limpio de un pasaje.

    Args:
        passage_id: Identificador del pasaje, ej. "JHN.3.16" o "PSA.23.1-6".

    Returns:
        dict con las claves:
            "texto"      → contenido limpio del versículo
            "referencia" → referencia legible, ej. "San Juan 3:16"
        None si ocurrió algún error.
    """
    global _cache

    # ── Devolver desde caché si el día coincide ───────────────────────────────
    hoy = date.today()
    if _cache["fecha"] == hoy and _cache["resultado"] is not None:
        return _cache["resultado"]

    # ── Construir URL ─────────────────────────────────────────────────────────
    ruta = _passage_to_url(passage_id)
    if not ruta:
        return None

    url = f"{_BASE_URL}{ruta}"

    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        versos = response.json()

        if not versos:
            logger.error("La API devolvió lista vacía para el pasaje %s", passage_id)
            return None

        texto, referencia = _limpiar_contenido(versos)
        resultado = {"texto": texto, "referencia": referencia}

        # ── Guardar en caché ──────────────────────────────────────────────────
        _cache["fecha"]     = hoy
        _cache["resultado"] = resultado

        return resultado

    except requests.exceptions.Timeout:
        logger.warning("Timeout al consultar el pasaje %s", passage_id)
    except requests.exceptions.ConnectionError:
        logger.error("No se pudo conectar a biblia-api.qhar.in para %s", passage_id)
    except requests.exceptions.HTTPError as exc:
        logger.error("Error HTTP %s para el pasaje %s: %s",
                     exc.response.status_code, passage_id, exc)
    except (KeyError, ValueError) as exc:
        logger.error("Respuesta inesperada de la API para el pasaje %s: %s", passage_id, exc)

    return None
