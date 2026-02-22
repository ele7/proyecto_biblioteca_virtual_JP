from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# ─────────────────────────────────────────────────────────────────────────────
# Versículo del Día — ADMIN y LECTOR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def versiculo_diario(request):
    """
    Muestra el versículo del día obtenido desde API.Bible (Reina Valera 1960).
    El pasaje cambia automáticamente cada día usando la fecha actual como índice.
    El resultado se cachea para evitar múltiples llamadas a la API.
    """
    from ..services.bible_api import get_pasaje_del_dia, obtener_versiculo

    passage_id = get_pasaje_del_dia()
    versiculo  = obtener_versiculo(passage_id)

    return render(request, "library/versiculo.html", {
        "versiculo":  versiculo,
        "passage_id": passage_id,
    })
