"""
test_views.py - tests for the HTML pages in events/views.py.

Django's test "client" acts like a browser: it sends GET/POST requests
and gives back the response so we can check the page content.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Event


def make_event(status="draft"):
    start = timezone.now() + timedelta(days=1)
    event = Event(
        title="Demo", start_time=start, end_time=start + timedelta(hours=1), status=status
    )
    event.save()
    return event


def form_time(dt):
    """Format a datetime the way the browser's datetime-local input sends it."""
    return timezone.localtime(dt).strftime("%Y-%m-%dT%H:%M")


@pytest.mark.django_db
def test_home_page_lists_events(client):
    make_event()
    response = client.get("/")
    assert response.status_code == 200
    assert "Demo" in response.content.decode()


@pytest.mark.django_db
def test_create_form_saves_valid_event(client):
    start = timezone.now() + timedelta(days=2)
    response = client.post(
        "/events/new/",
        {
            "title": "Party",
            "description": "",
            "start_time": form_time(start),
            "end_time": form_time(start + timedelta(hours=2)),
        },
    )
    event = Event.objects.get()
    assert response.status_code == 302  # redirect to the detail page
    assert response.url == f"/events/{event.pk}/"


@pytest.mark.django_db
def test_create_form_shows_model_errors(client):
    start = timezone.now() - timedelta(days=1)
    response = client.post(
        "/events/new/",
        {
            "title": "Party",
            "start_time": form_time(start),
            "end_time": form_time(start - timedelta(hours=1)),
        },
    )
    page = response.content.decode()
    assert response.status_code == 200  # form is shown again, not a crash
    assert "Start time cannot be in the past." in page
    assert "End time must be after the start time." in page
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_detail_page_shows_only_valid_next_status_buttons(client):
    event = make_event(status="draft")
    page = client.get(f"/events/{event.pk}/").content.decode()
    assert 'value="scheduled"' in page
    assert 'value="cancelled"' in page
    assert 'value="completed"' not in page
    assert 'value="in_progress"' not in page


@pytest.mark.django_db
def test_valid_status_change_from_web_page(client):
    event = make_event(status="draft")
    client.post(f"/events/{event.pk}/status/", {"status": "scheduled"})
    event.refresh_from_db()
    assert event.status == "scheduled"


@pytest.mark.django_db
def test_invalid_status_change_shows_error_instead_of_crashing(client):
    event = make_event(status="completed")
    response = client.post(f"/events/{event.pk}/status/", {"status": "draft"}, follow=True)
    assert response.status_code == 200
    assert "Cannot change status from" in response.content.decode()
    event.refresh_from_db()
    assert event.status == "completed"
