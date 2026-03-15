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