"""
services/carga_masiva.py
────────────────────────
Motor de carga masiva de libros desde un archivo Excel + ZIP.

Flujo:
  1. Lee el Excel con pandas (todo como string para evitar conversiones).
  2. Valida que existan las columnas obligatorias.
  3. Construye un índice {basename.lower(): ruta_interna} del ZIP.
  4. Cachea todas las Categorias en memoria (1 sola query).
  5. Procesa cada fila de forma independiente (savepoint por fila).
  6. Guarda archivos vía ContentFile a través del storage de Django.
  7. Retorna un resumen: {creados, errores, advertencias}.

Esta función NO lanza excepciones hacia arriba. Todos los errores
se capturan y se acumulan en las listas de resultados.
"""

import io
import logging
import zipfile

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction

from library.models import Categoria, Libro

logger = logging.getLogger(__name__)

# ─── Columnas que DEBEN existir en el Excel ───────────────────────────────────
COLUMNAS_REQUERIDAS = {'titulo', 'autor', 'año', 'categoria'}


# ─────────────────────────────────────────────────────────────────────────────
# Ayudantes privados
# ─────────────────────────────────────────────────────────────────────────────

def _construir_indice_zip(zip_file) -> dict:
    """
    Construye un dict {basename.lower(): ruta_interna_zip} desde un ZIP.

    Itera todos los miembros del ZIP (incluyendo subdirectorios) y usa
    solo el nombre base del archivo como clave.  Si hay colisiones de nombre,
    la última entrada gana (comportamiento documentado).

    Args:
        zip_file: InMemoryUploadedFile o TemporaryUploadedFile, o None.

    Returns:
        dict. Vacío si zip_file es None o si el ZIP está vacío.
    """
    if zip_file is None:
        return {}

    indice = {}
    try:
        zip_bytes = zip_file.read()
        zip_file.seek(0)            # rebobinar para usos posteriores

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for nombre_interno in zf.namelist():
                # Ignorar entradas de directorio
                if nombre_interno.endswith('/'):
                    continue
                # Usar solo el nombre base (soporta subcarpetas)
                partes   = nombre_interno.replace('\\', '/').split('/')
                basename = partes[-1].lower()
                if not basename:
                    continue
                if basename in indice:
                    logger.warning(
                        "ZIP: nombre duplicado '%s'. Se usará '%s' (ignorando '%s').",
                        basename, nombre_interno, indice[basename],
                    )
                indice[basename] = nombre_interno

    except zipfile.BadZipFile:
        logger.error("El archivo ZIP está dañado o no es un ZIP válido.")
    except Exception as exc:
        logger.error("Error leyendo el ZIP: %s", exc)

    return indice


def _extraer_bytes_zip(zip_file, ruta_interna: str) -> bytes | None:
    """
    Extrae el contenido de un miembro del ZIP como bytes.

    Rebobina `zip_file` antes y después de cada lectura, por lo que
    puede llamarse múltiples veces sobre el mismo objeto.

    Returns:
        bytes del archivo, o None si hubo un error.
    """
    try:
        zip_bytes = zip_file.read()
        zip_file.seek(0)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            return zf.read(ruta_interna)
    except Exception as exc:
        logger.error("Error extrayendo '%s' del ZIP: %s", ruta_interna, exc)
        return None


def _valor_str(valor) -> str:
    """Convierte un valor de celda pandas a string limpio. NaN → ''."""
    if pd.isna(valor):
        return ''
    return str(valor).strip()


def _valor_año(valor) -> int | None:
    """
    Convierte el valor de la columna 'año' a int válido.

    Returns:
        int entre 1000 y 2100, o None si el valor es inválido.
    """
    try:
        anio = int(float(str(valor).strip()))
        if 1000 <= anio <= 2100:
            return anio
        return None
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Función pública
# ─────────────────────────────────────────────────────────────────────────────

def procesar_carga_libros(excel_file, zip_file) -> dict:
    """
    Procesa la carga masiva de libros desde un Excel y un ZIP opcional.

    Args:
        excel_file: InMemoryUploadedFile del Excel (.xlsx).
        zip_file:   InMemoryUploadedFile del ZIP, o None si no se subió.

    Returns:
        dict con claves:
            'creados'      (int)   — libros creados exitosamente.
            'errores'      (list)  — [str, ...] mensajes de filas fallidas.
            'advertencias' (list)  — [str, ...] avisos no fatales.
    """
    resultado = {
        'creados':        0,
        'libros_creados': [],   # lista de instancias Libro para disparar notificaciones
        'errores':        [],
        'advertencias':   [],
    }

    # ── 1. Leer el Excel ──────────────────────────────────────────────────────
    try:
        df = pd.read_excel(excel_file, dtype=str)
    except Exception as exc:
        resultado['errores'].append(f"No se pudo leer el Excel: {exc}")
        return resultado

    # ── 2. Normalizar nombres de columnas ─────────────────────────────────────
    df.columns = [str(c).strip().lower() for c in df.columns]

    # ── 3. Validar columnas requeridas ────────────────────────────────────────
    columnas_faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if columnas_faltantes:
        resultado['errores'].append(
            f"El Excel no tiene las columnas requeridas: "
            f"{', '.join(sorted(columnas_faltantes))}. "
            f"Columnas encontradas: {', '.join(sorted(df.columns))}."
        )
        return resultado

    if df.empty:
        resultado['advertencias'].append("El Excel está vacío, no hay filas que procesar.")
        return resultado

    # ── 4. Construir índice del ZIP ───────────────────────────────────────────
    indice_zip = _construir_indice_zip(zip_file)
    if zip_file is not None and not indice_zip:
        resultado['advertencias'].append(
            "El ZIP estaba vacío o dañado. Se crearán los libros sin archivos adjuntos."
        )

    # ── 5. Cachear categorías (1 query) ───────────────────────────────────────
    cache_categorias = {
        cat.nombre.lower(): cat
        for cat in Categoria.objects.all()
    }

    # ── 6. Procesar fila por fila ─────────────────────────────────────────────
    for indice_fila, row in df.iterrows():
        num_display = int(indice_fila) + 2   # fila real en Excel (encabezado = 1)

        # ── 6a. Extraer valores ───────────────────────────────────────────────
        titulo           = _valor_str(row.get('titulo', ''))
        autor            = _valor_str(row.get('autor', ''))
        año_raw          = row.get('año', '')
        categoria_nombre = _valor_str(row.get('categoria', ''))
        isbn             = _valor_str(row.get('isbn', ''))
        descripcion      = _valor_str(row.get('descripcion', ''))
        nombre_pdf       = _valor_str(row.get('archivo_pdf', ''))
        nombre_portada   = _valor_str(row.get('portada', ''))

        # ── 6b. Validaciones de campos obligatorios ───────────────────────────
        if not titulo:
            resultado['errores'].append(
                f"Fila {num_display}: campo 'titulo' vacío. Fila omitida."
            )
            continue

        if not autor:
            resultado['errores'].append(
                f"Fila {num_display} ('{titulo}'): campo 'autor' vacío. Fila omitida."
            )
            continue

        anio = _valor_año(año_raw)
        if anio is None:
            resultado['errores'].append(
                f"Fila {num_display} ('{titulo}'): campo 'año' inválido "
                f"(valor: '{año_raw}'). Debe ser un número entre 1000 y 2100."
            )
            continue

        if not categoria_nombre:
            resultado['errores'].append(
                f"Fila {num_display} ('{titulo}'): campo 'categoria' vacío. Fila omitida."
            )
            continue

        # ── 6c. Resolver categoría ────────────────────────────────────────────
        categoria_obj = cache_categorias.get(categoria_nombre.lower())
        if categoria_obj is None:
            resultado['errores'].append(
                f"Fila {num_display} ('{titulo}'): la categoría '{categoria_nombre}' "
                f"no existe en la base de datos. Fila omitida."
            )
            continue

        # ── 6d. Detección de duplicados ───────────────────────────────────────
        # Primero por ISBN (si viene), después por (titulo, autor)
        if isbn:
            if Libro.objects.filter(isbn=isbn).exists():
                resultado['advertencias'].append(
                    f"Fila {num_display} ('{titulo}'): ya existe un libro con ISBN "
                    f"'{isbn}'. Fila omitida."
                )
                continue
        else:
            # Fallback: comparar título + autor
            if Libro.objects.filter(titulo__iexact=titulo, autor__iexact=autor).exists():
                resultado['advertencias'].append(
                    f"Fila {num_display}: ya existe un libro con título '{titulo}' "
                    f"y autor '{autor}'. Fila omitida."
                )
                continue

        # ── 6e. Resolver archivos del ZIP ─────────────────────────────────────
        contenido_pdf     = None
        contenido_portada = None

        if nombre_pdf:
            clave_pdf = nombre_pdf.lower()
            if clave_pdf in indice_zip:
                contenido_pdf = _extraer_bytes_zip(zip_file, indice_zip[clave_pdf])
                if contenido_pdf is None:
                    resultado['advertencias'].append(
                        f"Fila {num_display} ('{titulo}'): no se pudo leer "
                        f"'{nombre_pdf}' del ZIP. El libro se creará sin PDF."
                    )
            else:
                resultado['advertencias'].append(
                    f"Fila {num_display} ('{titulo}'): el archivo '{nombre_pdf}' "
                    f"no se encontró en el ZIP. El libro se creará sin PDF."
                )
        else:
            resultado['advertencias'].append(
                f"Fila {num_display} ('{titulo}'): no se indicó 'archivo_pdf'. "
                f"El libro se creará sin archivo PDF."
            )

        if nombre_portada:
            clave_portada = nombre_portada.lower()
            if clave_portada in indice_zip:
                contenido_portada = _extraer_bytes_zip(zip_file, indice_zip[clave_portada])
                if contenido_portada is None:
                    resultado['advertencias'].append(
                        f"Fila {num_display} ('{titulo}'): no se pudo leer "
                        f"'{nombre_portada}' del ZIP. El libro se creará sin portada."
                    )
            else:
                resultado['advertencias'].append(
                    f"Fila {num_display} ('{titulo}'): la portada '{nombre_portada}' "
                    f"no se encontró en el ZIP. El libro se creará sin portada."
                )
        # Si nombre_portada está vacío, no se emite advertencia (portada es opcional).

        # ── 6f. Crear el libro (savepoint por fila) ───────────────────────────
        try:
            with transaction.atomic():
                libro = Libro(
                    titulo      = titulo,
                    autor       = autor,
                    isbn        = isbn or None,   # None si vacío para respetar unique
                    año         = anio,
                    categoria   = categoria_obj,
                    descripcion = descripcion or None,
                )

                # Adjuntar PDF: save=False evita llamar libro.save() prematuramente.
                # Django invocará renombrar_archivo(libro, nombre_pdf) usando libro.titulo.
                if contenido_pdf:
                    libro.archivo.save(
                        nombre_pdf,
                        ContentFile(contenido_pdf),
                        save=False,
                    )

                # Adjuntar portada: upload_to="portadas/" → media/portadas/nombre
                if contenido_portada:
                    libro.portada.save(
                        nombre_portada,
                        ContentFile(contenido_portada),
                        save=False,
                    )

                # Persistir en la base de datos con todas las rutas ya asignadas
                libro.save()
                resultado['creados'] += 1
                resultado['libros_creados'].append(libro)

        except Exception as exc:
            logger.exception(
                "Error creando el libro '%s' (fila %d): %s", titulo, num_display, exc
            )
            resultado['errores'].append(
                f"Fila {num_display} ('{titulo}'): error inesperado al guardar: {exc}"
            )

    return resultado
