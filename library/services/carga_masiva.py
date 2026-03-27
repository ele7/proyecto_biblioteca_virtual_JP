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
import unicodedata
import zipfile

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction

from library.models import Categoria, Libro

logger = logging.getLogger(__name__)

# ─── Columnas que DEBEN existir en el Excel ───────────────────────────────────
COLUMNAS_REQUERIDAS = {'titulo', 'autor', 'categoria'}


# ─────────────────────────────────────────────────────────────────────────────
# Ayudantes privados
# ─────────────────────────────────────────────────────────────────────────────

def _quitar_tildes(texto: str) -> str:
    """Elimina diacríticos (tildes, diéresis, etc.) de un texto."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def _normalizar_nombre(nombre: str) -> str:
    """Normaliza un nombre de archivo: minúsculas y espacios → guiones bajos."""
    return nombre.lower().replace(' ', '_')


def _extraer_contenidos_zip(zip_bytes: bytes) -> dict:
    """
    Abre el ZIP UNA sola vez y retorna un dict {nombre_normalizado: bytes_del_archivo}.

    La clave se normaliza (minúsculas + espacios→guiones bajos) para que los
    nombres con espacios en el ZIP coincidan con los nombres con guiones bajos
    del Excel (y viceversa).

    Returns:
        dict. Vacío si zip_bytes está vacío o el ZIP es inválido.
    """
    contenidos = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for nombre_interno in zf.namelist():
                if nombre_interno.endswith('/'):
                    continue
                partes   = nombre_interno.replace('\\', '/').split('/')
                basename = _normalizar_nombre(partes[-1])
                if not basename:
                    continue
                if basename in contenidos:
                    logger.warning(
                        "ZIP: nombre duplicado '%s'. Se usará la primera aparición.",
                        basename,
                    )
                    continue
                try:
                    contenidos[basename] = zf.read(nombre_interno)
                except Exception as exc:
                    logger.error("Error leyendo '%s' del ZIP: %s", nombre_interno, exc)

    except zipfile.BadZipFile:
        logger.error("El archivo ZIP está dañado o no es un ZIP válido.")
    except Exception as exc:
        logger.error("Error leyendo el ZIP: %s", exc)

    return contenidos


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
    df.columns = [_quitar_tildes(str(c).strip().lower()) for c in df.columns]

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

    # ── 4. Leer el ZIP una sola vez y extraer TODOS los archivos en memoria ─────
    contenidos_zip = {}
    if zip_file is not None:
        zip_bytes = zip_file.read()
        contenidos_zip = _extraer_contenidos_zip(zip_bytes)
        if not contenidos_zip:
            resultado['advertencias'].append(
                "El ZIP estaba vacío o dañado. Se crearán los libros sin archivos adjuntos."
            )

    # ── 5. Cachear categorías (1 query) ───────────────────────────────────────
    cache_categorias = {
        cat.nombre.lower(): cat
        for cat in Categoria.objects.all()
    }

    # ── 5b. Pre-cargar duplicados existentes (evita N queries en el loop) ─────
    isbn_existentes = set(
        Libro.objects.exclude(isbn__isnull=True).exclude(isbn='')
        .values_list('isbn', flat=True)
    )
    titulos_autores_existentes = {
        (t.lower(), a.lower())
        for t, a in Libro.objects.values_list('titulo', 'autor')
    }

    # ── 6. Procesar fila por fila ─────────────────────────────────────────────
    for indice_fila, row in df.iterrows():
        num_display = int(indice_fila) + 2   # fila real en Excel (encabezado = 1)

        # ── 6a. Extraer valores ───────────────────────────────────────────────
        titulo           = _valor_str(row.get('titulo', ''))
        autor            = _valor_str(row.get('autor', ''))
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

        año_raw = row.get('año', '') if 'año' in df.columns else ''
        anio    = _valor_año(año_raw)
        if año_raw and _valor_str(año_raw) and anio is None:
            resultado['advertencias'].append(
                f"Fila {num_display} ('{titulo}'): campo 'año' inválido "
                f"(valor: '{año_raw}'). Se guardará sin año."
            )

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

        # ── 6d. Detección de duplicados: actualizar portada si falta ─────────
        libro_existente = None
        if isbn:
            if isbn in isbn_existentes:
                libro_existente = Libro.objects.filter(isbn=isbn).first()
        else:
            if (titulo.lower(), autor.lower()) in titulos_autores_existentes:
                libro_existente = Libro.objects.filter(
                    titulo__iexact=titulo, autor__iexact=autor
                ).first()

        if libro_existente is not None:
            # Si ya tiene portada, omitir sin más
            if libro_existente.portada:
                resultado['advertencias'].append(
                    f"Fila {num_display} ('{titulo}'): ya existe y ya tiene portada. Fila omitida."
                )
                continue

            # Sin portada → intentar asignarla desde el ZIP
            nombre_portada_dup = _valor_str(row.get('portada', ''))
            if nombre_portada_dup:
                clave = _normalizar_nombre(nombre_portada_dup)
                bytes_portada = contenidos_zip.get(clave)
                if bytes_portada:
                    try:
                        libro_existente.portada.save(
                            nombre_portada_dup,
                            ContentFile(bytes_portada),
                            save=True,
                        )
                        resultado['advertencias'].append(
                            f"Fila {num_display} ('{titulo}'): libro existente actualizado con portada."
                        )
                    except Exception as exc:
                        resultado['advertencias'].append(
                            f"Fila {num_display} ('{titulo}'): libro existente pero no se pudo "
                            f"guardar la portada: {exc}."
                        )
                else:
                    resultado['advertencias'].append(
                        f"Fila {num_display} ('{titulo}'): libro existente sin portada, "
                        f"pero '{nombre_portada_dup}' no se encontró en el ZIP."
                    )
            else:
                resultado['advertencias'].append(
                    f"Fila {num_display} ('{titulo}'): ya existe y no se indicó portada. Fila omitida."
                )
            continue

        # ── 6e. Resolver archivos del ZIP (ya están en memoria) ───────────────
        contenido_pdf     = None
        contenido_portada = None

        if nombre_pdf:
            clave_pdf = _normalizar_nombre(nombre_pdf)
            if clave_pdf in contenidos_zip:
                contenido_pdf = contenidos_zip[clave_pdf]
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
            clave_portada = _normalizar_nombre(nombre_portada)
            if clave_portada in contenidos_zip:
                contenido_portada = contenidos_zip[clave_portada]
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
                # Actualizar los sets en memoria para detectar duplicados
                # entre filas del mismo Excel sin nuevas queries
                if isbn:
                    isbn_existentes.add(isbn)
                titulos_autores_existentes.add((titulo.lower(), autor.lower()))

        except Exception as exc:
            logger.exception(
                "Error creando el libro '%s' (fila %d): %s", titulo, num_display, exc
            )
            resultado['errores'].append(
                f"Fila {num_display} ('{titulo}'): error inesperado al guardar: {exc}"
            )

    return resultado


def procesar_actualizacion_libros(excel_file, zip_file) -> dict:
    """
    Actualiza libros existentes desde un Excel + ZIP opcional.

    - Busca cada libro por ISBN (si viene) o por título + autor.
    - Actualiza solo los campos no vacíos del Excel.
    - Si el ZIP trae un nuevo PDF o portada, los reemplaza.
    - Si el libro no existe, lo reporta como advertencia (no lo crea).
    """
    resultado = {
        'actualizados': 0,
        'errores':      [],
        'advertencias': [],
    }

    # ── 1. Leer el Excel ──────────────────────────────────────────────────────
    try:
        df = pd.read_excel(excel_file, dtype=str)
    except Exception as exc:
        resultado['errores'].append(f"No se pudo leer el Excel: {exc}")
        return resultado

    df.columns = [_quitar_tildes(str(c).strip().lower()) for c in df.columns]

    if 'isbn' not in df.columns and ('titulo' not in df.columns or 'autor' not in df.columns):
        resultado['errores'].append(
            "El Excel debe tener columna 'isbn', o bien 'titulo' y 'autor' para identificar los libros."
        )
        return resultado

    if df.empty:
        resultado['advertencias'].append("El Excel está vacío, no hay filas que procesar.")
        return resultado

    # ── 2. Leer el ZIP ────────────────────────────────────────────────────────
    contenidos_zip = {}
    if zip_file is not None:
        zip_bytes = zip_file.read()
        contenidos_zip = _extraer_contenidos_zip(zip_bytes)
        if not contenidos_zip:
            resultado['advertencias'].append(
                "El ZIP estaba vacío o dañado. Se actualizarán los libros sin reemplazar archivos."
            )

    # ── 3. Cachear categorías ─────────────────────────────────────────────────
    cache_categorias = {cat.nombre.lower(): cat for cat in Categoria.objects.all()}

    # ── 4. Procesar fila por fila ─────────────────────────────────────────────
    for indice_fila, row in df.iterrows():
        num_display = int(indice_fila) + 2

        isbn   = _valor_str(row.get('isbn', ''))
        titulo = _valor_str(row.get('titulo', ''))
        autor  = _valor_str(row.get('autor', ''))

        # ── 4a. Buscar libro existente ────────────────────────────────────────
        libro = None
        if isbn:
            libro = Libro.objects.filter(isbn=isbn).first()
        elif titulo and autor:
            libro = Libro.objects.filter(titulo__iexact=titulo, autor__iexact=autor).first()
        else:
            resultado['errores'].append(
                f"Fila {num_display}: sin ISBN ni título+autor para identificar el libro. Fila omitida."
            )
            continue

        if libro is None:
            resultado['advertencias'].append(
                f"Fila {num_display} ('{titulo or isbn}'): no se encontró en la base de datos. Fila omitida."
            )
            continue

        # ── 4b. Actualizar campos no vacíos ───────────────────────────────────
        campos_modificados = []
        try:
            with transaction.atomic():
                if titulo and titulo.lower() != libro.titulo.lower():
                    libro.titulo = titulo
                    campos_modificados.append('titulo')

                if autor and autor.lower() != libro.autor.lower():
                    libro.autor = autor
                    campos_modificados.append('autor')

                descripcion = _valor_str(row.get('descripcion', ''))
                if descripcion:
                    libro.descripcion = descripcion
                    campos_modificados.append('descripcion')

                año_raw = row.get('año', '') if 'año' in df.columns else ''
                anio = _valor_año(año_raw)
                if anio is not None:
                    libro.año = anio
                    campos_modificados.append('año')

                categoria_nombre = _valor_str(row.get('categoria', ''))
                if categoria_nombre:
                    categoria_obj = cache_categorias.get(categoria_nombre.lower())
                    if categoria_obj:
                        libro.categoria = categoria_obj
                        campos_modificados.append('categoria')
                    else:
                        resultado['advertencias'].append(
                            f"Fila {num_display} ('{libro.titulo}'): categoría '{categoria_nombre}' "
                            f"no existe. Se mantiene la categoría actual."
                        )

                # ── 4c. Reemplazar archivos del ZIP ───────────────────────────
                nombre_pdf     = _valor_str(row.get('archivo_pdf', ''))
                nombre_portada = _valor_str(row.get('portada', ''))

                if nombre_pdf:
                    clave_pdf = _normalizar_nombre(nombre_pdf)
                    bytes_pdf = contenidos_zip.get(clave_pdf)
                    if bytes_pdf:
                        libro.archivo.save(nombre_pdf, ContentFile(bytes_pdf), save=False)
                        campos_modificados.append('archivo_pdf')
                    else:
                        resultado['advertencias'].append(
                            f"Fila {num_display} ('{libro.titulo}'): '{nombre_pdf}' no encontrado en el ZIP."
                        )

                if nombre_portada:
                    clave_portada = _normalizar_nombre(nombre_portada)
                    bytes_portada = contenidos_zip.get(clave_portada)
                    if bytes_portada:
                        libro.portada.save(nombre_portada, ContentFile(bytes_portada), save=False)
                        campos_modificados.append('portada')
                    else:
                        resultado['advertencias'].append(
                            f"Fila {num_display} ('{libro.titulo}'): '{nombre_portada}' no encontrado en el ZIP."
                        )

                libro.save()
                resultado['actualizados'] += 1

                if not campos_modificados:
                    resultado['advertencias'].append(
                        f"Fila {num_display} ('{libro.titulo}'): no había cambios que aplicar."
                    )

        except Exception as exc:
            logger.exception("Error actualizando '%s' (fila %d): %s", libro.titulo, num_display, exc)
            resultado['errores'].append(
                f"Fila {num_display} ('{libro.titulo}'): error inesperado al actualizar: {exc}"
            )

    return resultado
