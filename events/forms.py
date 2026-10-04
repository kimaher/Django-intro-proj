"""
forms.py - the HTML form used on the "New event" page.

A ModelForm builds form fields straight from the Event model. When the form
is validated with form.is_valid(), Django also calls Event.full_clean(), so
the model's rules (past start time, start before end) show up as form
errors automatically. There is no validation logic in this file.
"""

from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        # status is left out: new events always start as "draft" (the model default).
        fields = ["title", "description", "start_time", "end_time"]
        # Use the browser's built-in date/time picker for the time fields.
        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "end_time": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
