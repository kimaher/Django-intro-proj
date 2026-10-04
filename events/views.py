"""
views.py - functions that handle requests for the HTML web pages.

Each view receives a request, talks to the Event model, and returns a
rendered template. Views do not contain business rules; when the model
rejects something it raises ValidationError, and the view shows the message.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EventForm
from .models import Event


def event_list(request):
    """Home page: list all events."""
    events = Event.objects.all()
    return render(request, "events/event_list.html", {"events": events})


def event_create(request):
    """Show the 'New event' form, and save it when submitted."""
    if request.method == "POST":
        # Fill the form with what the user submitted.
        form = EventForm(request.POST)
        # is_valid() runs the form field checks AND Event.full_clean(),
        # so the model's error messages get attached to the form here.
        if form.is_valid():
            event = form.save()
            messages.success(request, f"Event '{event.title}' created.")
            return redirect("event_detail", pk=event.pk)
    else:
        # GET request: show an empty form.
        form = EventForm()

    # Either a fresh form, or a form with error messages to display.
    return render(request, "events/event_form.html", {"form": form})


def event_detail(request, pk):
    """Show one event, with buttons for its valid next statuses."""
    event = get_object_or_404(Event, pk=pk)
    return render(request, "events/event_detail.html", {"event": event})


def event_change_status(request, pk):
    """Handle a click on one of the status buttons on the detail page."""
    event = get_object_or_404(Event, pk=pk)

    # Only accept form submissions; a plain visit just goes back to the page.
    if request.method != "POST":
        return redirect("event_detail", pk=event.pk)

    event.status = request.POST.get("status", "")
    try:
        # save() calls full_clean(), which checks the status transition.
        event.save()
        messages.success(request, f"Status changed to '{event.get_status_display()}'.")
    except ValidationError as error:
        # The model said no. Show its message(s) instead of crashing.
        for message in error.messages:
            messages.error(request, message)

    return redirect("event_detail", pk=event.pk)
