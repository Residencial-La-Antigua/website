from typing import ClassVar

from django import forms

from .models import Event
from .recurrence import MAX_OCCURRENCES


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = (
            "title",
            "description",
            "location",
            "meeting_link",
            "start_at",
            "end_at",
        )
        widgets: ClassVar = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class RecurrenceForm(forms.Form):
    FREQUENCY_CHOICES = (
        ("weekly", "Semanal"),
        ("monthly", "Mensual"),
    )

    is_recurring = forms.BooleanField(required=False)
    frequency = forms.ChoiceField(choices=FREQUENCY_CHOICES, required=False)
    end_date = forms.DateField(required=False)
    occurrence_count = forms.IntegerField(
        required=False, min_value=1, max_value=MAX_OCCURRENCES
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("is_recurring"):
            return cleaned_data

        if not cleaned_data.get("frequency"):
            self.add_error("frequency", "Seleccione una frecuencia.")

        end_date = cleaned_data.get("end_date")
        occurrence_count = cleaned_data.get("occurrence_count")
        if bool(end_date) == bool(occurrence_count):
            message = (
                "Indique una fecha final o un número de repeticiones, no ambos."
            )
            self.add_error("end_date", message)
            self.add_error("occurrence_count", message)

        return cleaned_data
