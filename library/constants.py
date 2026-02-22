"""
Constantes del sistema. Sin dependencias de Django ni del proyecto.
Importar desde aquí en lugar de usar strings literales en el código.
"""


class RolNombre:
    """
    Única fuente de verdad para los nombres de rol.

    Uso correcto:
        from .constants import RolNombre
        if user.rol.nombre == RolNombre.ADMIN: ...
    """
    ADMIN  = 'ADMIN'
    LECTOR = 'LECTOR'

    CHOICES = [
        (ADMIN,  'Administrador'),
        (LECTOR, 'Lector'),
    ]
