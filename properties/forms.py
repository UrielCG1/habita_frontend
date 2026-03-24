from django import forms


class RentalRequestForm(forms.Form):
    message = forms.CharField(
        label="Mensaje",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Cuéntale al propietario un poco sobre tu interés por esta propiedad...",
                "class": "form-textarea",
            }
        ),
    )

    move_in_date = forms.DateField(
        label="Fecha propuesta de visita",
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-input",
            }
        ),
    )

    monthly_budget = forms.DecimalField(
        label="Presupuesto mensual",
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Ej. 12000",
                "class": "form-input",
            }
        ),
    )


class ReviewForm(forms.Form):
    rating = forms.ChoiceField(
        label="Calificación",
        choices=(
            ("5", "5 estrellas"),
            ("4", "4 estrellas"),
            ("3", "3 estrellas"),
            ("2", "2 estrellas"),
            ("1", "1 estrella"),
        ),
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    comment = forms.CharField(
        label="Comentario",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Comparte tu experiencia con esta propiedad...",
                "class": "form-textarea",
            }
        ),
    )