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


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def clean(self, data, initial=None):
        if not data:
            return []

        single_clean = super().clean

        if isinstance(data, (list, tuple)):
            files = data
        else:
            files = [data]

        return [single_clean(file, initial) for file in files]


class OwnerPropertyForm(forms.Form):
    title = forms.CharField(
        label="Título",
        max_length=180,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Departamento con terraza en el centro"}),
    )
    description = forms.CharField(
        label="Descripción",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 5, "placeholder": "Describe la propiedad..."}),
    )
    price = forms.DecimalField(
        label="Precio mensual",
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "9000.00"}),
    )
    property_type = forms.ChoiceField(
        label="Tipo de propiedad",
        choices=[
            ("house", "Casa"),
            ("apartment", "Departamento"),
            ("room", "Habitación"),
            ("studio", "Estudio"),
            ("land", "Terreno"),
            ("commercial", "Comercial"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        label="Estado",
        choices=[
            ("available", "Disponible"),
            ("rented", "Rentada"),
            ("maintenance", "En mantenimiento"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    address_line = forms.CharField(
        label="Dirección",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Av. Peñuelas 120"}),
    )
    neighborhood = forms.CharField(
        label="Colonia",
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Los Vitrales"}),
    )
    city = forms.CharField(
        label="Ciudad",
        max_length=100,
        initial="Querétaro",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Querétaro"}),
    )
    state = forms.CharField(
        label="Estado",
        max_length=100,
        initial="Querétaro",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Querétaro"}),
    )
    postal_code = forms.CharField(
        label="Código postal",
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. 76150"}),
    )

    bedrooms = forms.IntegerField(
        label="Recámaras",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "2"}),
    )
    bathrooms = forms.IntegerField(
        label="Baños",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "2"}),
    )
    parking_spaces = forms.IntegerField(
        label="Estacionamientos",
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "1"}),
    )
    area_m2 = forms.DecimalField(
        label="Área m²",
        min_value=0,
        required=False,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "140.00"}),
    )

    latitude = forms.DecimalField(required=False, decimal_places=7, max_digits=10, widget=forms.HiddenInput())
    longitude = forms.DecimalField(required=False, decimal_places=7, max_digits=10, widget=forms.HiddenInput())

    is_published = forms.BooleanField(
        label="Publicada",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

    images = MultipleImageField(
        label="Imágenes",
        required=False,
        widget=MultipleImageInput(attrs={"class": "form-input-file"}),
    )