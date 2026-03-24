from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "tu_correo@ejemplo.com",
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Ingresa tu contraseña",
                "autocomplete": "current-password",
            }
        ),
    )


class RegisterForm(forms.Form):
    full_name = forms.CharField(
        label="Nombre completo",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Tu nombre completo",
                "autocomplete": "name",
            }
        ),
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "tu_correo@ejemplo.com",
                "autocomplete": "email",
            }
        ),
    )

    phone = forms.CharField(
        label="Teléfono",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "4420000000",
                "autocomplete": "tel",
            }
        ),
    )

    role = forms.ChoiceField(
        label="Tipo de cuenta",
        choices=(
            ("tenant", "Quiero rentar"),
            ("owner", "Quiero publicar propiedades"),
        ),
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    password = forms.CharField(
        label="Contraseña",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Mínimo 8 caracteres",
                "autocomplete": "new-password",
            }
        ),
    )

    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Repite tu contraseña",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Las contraseñas no coinciden.")

        return cleaned_data


class OwnerRequestStatusForm(forms.Form):
    status = forms.ChoiceField(
        label="Nuevo estado",
        choices=(
            ("pending", "Pendiente"),
            ("accepted", "Aceptada"),
            ("rejected", "Rechazada"),
            ("cancelled", "Cancelada"),
        ),
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    owner_notes = forms.CharField(
        label="Notas del propietario",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-textarea",
                "placeholder": "Notas internas o respuesta para esta solicitud...",
            }
        ),
    )


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop("widget_attrs", {}) or {}
        attrs.setdefault("class", "form-input")
        attrs.setdefault("accept", "image/*")
        kwargs.setdefault("widget", MultipleFileInput(attrs=attrs))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]

        return single_file_clean(data, initial)


class OwnerPropertyForm(forms.Form):
    title = forms.CharField(
        label="Título",
        max_length=180,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Ej. Departamento céntrico en Querétaro",
                "maxlength": "180",
            }
        ),
    )
    description = forms.CharField(
        label="Descripción",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 5,
                "placeholder": "Describe la propiedad, lo que la hace especial y el perfil ideal del inquilino.",
            }
        ),
    )
    price = forms.DecimalField(
        label="Precio mensual",
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "placeholder": "Ej. 12000",
                "min": "0",
                "step": "0.01",
            }
        ),
    )
    property_type = forms.ChoiceField(
        label="Tipo de propiedad",
        choices=(
            ("house", "Casa"),
            ("apartment", "Departamento"),
            ("studio", "Estudio"),
            ("room", "Habitación"),
            ("land", "Terreno"),
            ("office", "Oficina"),
            ("commercial", "Local comercial"),
        ),
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    status = forms.ChoiceField(
        label="Estado comercial",
        choices=(
            ("available", "Disponible"),
            ("occupied", "Ocupada"),
            ("rented", "Rentada"),
            ("paused", "Pausada"),
            ("hidden", "Oculta (legacy)"),
        ),
        widget=forms.Select(attrs={"class": "form-input"}),
    )

    address_line = forms.CharField(
        label="Dirección",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Calle, número, interior"}),
    )
    neighborhood = forms.CharField(
        label="Colonia",
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Centro"}),
    )
    city = forms.CharField(
        label="Ciudad",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Querétaro"}),
    )
    state = forms.CharField(
        label="Estado",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Querétaro"}),
    )

    bedrooms = forms.IntegerField(
        label="Recámaras",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
    )
    bathrooms = forms.IntegerField(
        label="Baños",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
    )
    parking_spaces = forms.IntegerField(
        label="Espacios de estacionamiento",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
    )
    area_m2 = forms.DecimalField(
        label="Área en m²",
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-input", "min": "0", "step": "0.01", "placeholder": "Ej. 87.5"}),
    )

    latitude = forms.DecimalField(
        label="Latitud",
        required=False,
        decimal_places=7,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.0000001", "placeholder": "20.5888000"}),
    )
    longitude = forms.DecimalField(
        label="Longitud",
        required=False,
        decimal_places=7,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-input", "step": "0.0000001", "placeholder": "-100.3899000"}),
    )

    is_published = forms.BooleanField(
        label="Publicar propiedad",
        required=False,
    )

    images = MultipleFileField(
        label="Imágenes",
        required=False,
        widget_attrs={
            "class": "form-input",
            "accept": "image/*",
        },
    )
