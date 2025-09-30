from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import Categoria,Rol ,Libro, CategoriaPermitida, CustomUser


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)

@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "autor", "categoria")
    list_filter = ("categoria",)
    search_fields = ("titulo", "autor")

class CategoriaPermitidaInline(admin.TabularInline):
    model = CategoriaPermitida
    extra = 1
    autocomplete_fields = ['categoria']

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    ordering = ['email']
    list_display = ['email', 'rol', 'is_active','get_categorias']
    list_filter = ['rol', 'is_active']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permisos', {'fields': ('is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Información adicional', {'fields': ('rol',)}),  
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'rol', 'is_active')  
        }),
    )
    search_fields = ('email',)
    inlines = [CategoriaPermitidaInline]
    
    def get_categorias(self, obj):
        return ", ".join([c.nombre for c in obj.categorias.all()])
    get_categorias.short_description = "Categorías"
    

admin.site.register(CustomUser, CustomUserAdmin)
