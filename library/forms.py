from django import forms
from .models import Libro, Categoria, CustomUser, CategoriaPermitida, SolicitudLibro, Reflexion
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

User = get_user_model()


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'password', 'rol']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']

class LibroForm(forms.ModelForm):
    class Meta:
        model = Libro
        fields = ['titulo', 'autor','año','categoria', 'descripcion','portada','archivo']
        widgets = {
            'titulo'     : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del libro'}),
            'autor'      : forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Autor'}),
            'año'        : forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria'  : forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'portada'    : forms.FileInput(attrs={'class': 'form-control'}),
            'archivo'    : forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['archivo'].required = False

class CustomUserCreationForm(UserCreationForm):
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'form-check-input'}  # clase para checkboxes de Bootstrap
        )
    )
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('name', 'email', 'rol', 'categorias', 'is_active')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.categoriapermitida_set.all().delete()
            for cat in self.cleaned_data['categorias']:
                CategoriaPermitida.objects.create(usuario=user, categoria=cat)
        return user


class CustomUserChangeForm(forms.ModelForm):
    # Campo de contraseña opcional
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña (dejar vacío para no cambiar)'
        }),
        label="Contraseña"
    )

    # Campo para seleccionar categorías permitidas
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'form-check-input'}
        ),
        label="Categorías permitidas"
    )

    class Meta:
        model = CustomUser
        # ❌ NO incluimos 'password' aquí
        fields = ('name', 'email', 'rol', 'categorias', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Inicializar las categorías del usuario
            self.fields['categorias'].initial = self.instance.categoriapermitida_set.values_list('categoria_id', flat=True)

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            # Solo cambiar la contraseña si se ingresó algo
            user.set_password(password)
        if commit:
            user.save()
            # Actualizar categorías
            user.categoriapermitida_set.all().delete()
            for cat in self.cleaned_data.get('categorias', []):
                CategoriaPermitida.objects.create(usuario=user, categoria=cat)
        return user
    
class CustomUserEditForm(forms.ModelForm):
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class':'form-control'}))
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class':'form-check-input'})
    )

    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'rol', 'categorias', 'is_active', 'password']
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control'}),
            'email': forms.EmailInput(attrs={'class':'form-control'}),
            'rol': forms.Select(attrs={'class':'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
    # Solo cambiar contraseña si se ingresó
        password = self.cleaned_data.get('password')
        if password:
         user.set_password(password)  # Genera el hash correctamente
        if commit:
            user.save()
        # Actualizar categorías
            user.categoriapermitida_set.all().delete()
            for cat in self.cleaned_data.get('categorias', []):
                CategoriaPermitida.objects.create(usuario=user, categoria=cat)
        return user
    
class UploadUsersForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo de usuarios (.xlsx o .csv)",
        help_text=(
            "Columnas obligatorias: email, rol. "
            "Opcionales: name, password, categorias."
        ),
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls,.csv'}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            ext = archivo.name.split('.')[-1].lower()
            if ext not in ('xlsx', 'xls', 'csv'):
                raise forms.ValidationError(
                    "Solo se aceptan archivos Excel (.xlsx) o CSV (.csv)."
                )
        return archivo


class CargaMasivaLibrosForm(forms.Form):
    """
    Formulario para la carga masiva de libros.

    Acepta un Excel (.xlsx) con los metadatos de los libros y un ZIP
    opcional con los PDFs y portadas referenciados en el Excel.
    """
    MODO_CHOICES = [
        ('crear',      'Crear nuevos libros'),
        ('actualizar', 'Actualizar libros existentes'),
    ]
    modo = forms.ChoiceField(
        choices=MODO_CHOICES,
        initial='crear',
        widget=forms.RadioSelect,
        label='Modo de operación',
    )
    archivo_excel = forms.FileField(
        label="Archivo Excel (.xlsx)",
        help_text=(
            "Columnas obligatorias: titulo, autor, año, categoria. "
            "Opcionales: isbn, descripcion, archivo_pdf, portada."
        ),
        widget=forms.FileInput(attrs={'accept': '.xlsx'}),
    )
    archivo_zip = forms.FileField(
        label="Archivo ZIP con PDFs y portadas",
        required=False,
        help_text=(
            "Opcional. Puede contener subcarpetas. "
            "Los nombres de archivo deben coincidir con los indicados en el Excel."
        ),
        widget=forms.FileInput(attrs={'accept': '.zip'}),
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo and not archivo.name.lower().endswith('.xlsx'):
            raise forms.ValidationError("Solo se aceptan archivos Excel (.xlsx).")
        return archivo

    def clean_archivo_zip(self):
        archivo = self.cleaned_data.get('archivo_zip')
        if archivo and not archivo.name.lower().endswith('.zip'):
            raise forms.ValidationError("El archivo de medios debe ser un ZIP (.zip).")
        return archivo


class CambioPasswordForm(forms.Form):
    """Formulario self-service para que el usuario cambie su propia contraseña."""
    password_actual = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white/10 border border-white/20 text-navy placeholder-gray-400 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-gold transition-colors',
            'placeholder': '••••••••',
        }),
    )
    password_nuevo = forms.CharField(
        label="Nueva contraseña",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white/10 border border-white/20 text-navy placeholder-gray-400 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-gold transition-colors',
            'placeholder': 'Mínimo 8 caracteres',
        }),
    )
    password_confirmar = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white/10 border border-white/20 text-navy placeholder-gray-400 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-gold transition-colors',
            'placeholder': 'Repite la nueva contraseña',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password_nuevo')
        p2 = cleaned_data.get('password_confirmar')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas nuevas no coinciden.")
        return cleaned_data


class ReflexionForm(forms.ModelForm):
    class Meta:
        model  = Reflexion
        fields = ['titulo', 'cuerpo', 'autor_nombre']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-navy focus:outline-none focus:border-gold transition-colors',
                'placeholder': 'Título de la reflexión',
            }),
            'cuerpo': forms.Textarea(attrs={
                'class': 'w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-navy focus:outline-none focus:border-gold transition-colors resize-none',
                'rows': 5,
                'placeholder': 'Escribe el contenido de la reflexión...',
            }),
            'autor_nombre': forms.TextInput(attrs={
                'class': 'w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-navy focus:outline-none focus:border-gold transition-colors',
                'placeholder': 'Nombre del autor',
            }),
        }
        labels = {
            'titulo':      'Título',
            'cuerpo':      'Contenido',
            'autor_nombre': '¿Quién lo escribió?',
        }


class OlvidoPasswordForm(forms.Form):
    """Formulario para solicitar restablecimiento de contraseña por email."""
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-white/10 border border-white/20 text-white placeholder-white/40 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-gold focus:bg-white/15 transition-colors',
            'placeholder': 'correo@ejemplo.com',
        }),
    )


class SolicitudLibroForm(forms.ModelForm):
    class Meta:
        model  = SolicitudLibro
        fields = ['titulo_sugerido', 'autor_sugerido', 'nota']
        widgets = {
            'titulo_sugerido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del libro que deseas'
            }),
            'autor_sugerido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Autor (opcional)'
            }),
            'nota': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Información adicional o comentario (opcional)'
            }),
        }
        labels = {
            'titulo_sugerido': 'Título del libro',
            'autor_sugerido':  'Autor',
            'nota':            'Nota adicional',
        }