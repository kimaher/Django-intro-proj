"""
test_api.py - tests for the JSON API in events/api_views.py.

The main goal: when the model rejects data, the API must answer with
HTTP 400 (bad request), not 500 (server crash).
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event

LIST_URL = "/api/events/"


def detail_url(pk):
    return f"/api/events/{pk}/"


def future_times(days=1):
    """Return (start, end) ISO strings for a one-hour event in the future."""
    start = timezone.now() + timedelta(days=days)
    return start.isoformat(), (start + timedelta(hours=1)).isoformat()


@pytest.fixture
def api_client():
    """A test client that speaks JSON, provided by DRF."""
    return APIClient()


@pytest.fixture
def event():
    start = timezone.now() + timedelta(days=1)
    e = Event(title="Existing", start_time=start, end_time=start + timedelta(hours=1))
    e.save()
    return e


# ---------- Success cases ----------

@pytest.mark.django_db
def test_list_events(api_client, event):
    response = api_client.get(LIST_URL)
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Existing"


@pytest.mark.django_db
def test_create_event(api_client):
    start, end = future_times()
    response = api_client.post(
        LIST_URL, {"title": "Launch", "start_time": start, "end_time": end}, format="json"
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert Event.objects.count() == 1


@pytest.mark.django_db
def test_update_status_with_valid_transition(api_client, event):
    response = api_client.patch(detail_url(event.pk), {"status": "scheduled"}, format="json")
    assert response.status_code == 200
    event.refresh_from_db()
    assert event.status == "scheduled"


# ---------- 400 cases ----------

@pytest.mark.django_db
def test_create_with_past_start_time_returns_400(api_client):
    start = timezone.now() - timedelta(days=1)
    response = api_client.post(
        LIST_URL,
        {
            "title": "Too late",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 400
    assert "start_time" in response.json()
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_create_with_start_after_end_returns_400(api_client):
    start, end = future_times()
    response = api_client.post(
        LIST_URL, {"title": "Backwards", "start_time": end, "end_time": start}, format="json"
    )
    assert response.status_code == 400
    assert "end_time" in response.json()


@pytest.mark.django_db
def test_create_with_missing_fields_returns_400(api_client):
    response = api_client.post(LIST_URL, {}, format="json")
    assert response.status_code == 400
    assert "title" in response.json()


@pytest.mark.django_db
def test_invalid_status_transition_returns_400(api_client, event):
    # draft -> completed is not allowed
    response = api_client.patch(detail_url(event.pk), {"status": "completed"}, format="json")
    assert response.status_code == 400
    assert "status" in response.json()
    event.refresh_from_db()
    assert event.status == "draft"


@pytest.mark.django_db
def test_update_making_start_after_end_returns_400(api_client, event):
    new_end = (event.start_time - timedelta(hours=1)).isoformat()
    response = api_client.patch(detail_url(event.pk), {"end_time": new_end}, format="json")
    assert response.status_code == 400
    assert "end_time" in response.json()
