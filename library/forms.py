from django import forms
from .models import Libro, Categoria , CustomUser, CategoriaPermitida
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
    archivo = forms.FileField(label="Archivo CSV de usuarios")    