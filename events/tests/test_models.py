"""
test_models.py - tests for the rules in events/models.py.

These tests call event.save() directly (no web pages, no API) to prove
the model enforces every rule on its own.

@pytest.mark.django_db gives each test access to a fresh test database.
"""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from events.models import Event


def make_event(status=Event.STATUS_DRAFT, **kwargs):
    """Create and save an event starting tomorrow, lasting one hour."""
    start = timezone.now() + timedelta(days=1)
    data = {
        "title": "Team meeting",
        "start_time": start,
        "end_time": start + timedelta(hours=1),
        "status": status,
    }
    data.update(kwargs)
    event = Event(**data)
    event.save()
    return event


# ---------- Time rules ----------

@pytest.mark.django_db
def test_valid_event_is_saved():
    event = make_event()
    assert event.pk is not None
    assert event.status == Event.STATUS_DRAFT


@pytest.mark.django_db
def test_start_time_in_the_past_is_rejected():
    yesterday = timezone.now() - timedelta(days=1)
    with pytest.raises(ValidationError) as error:
        make_event(start_time=yesterday, end_time=yesterday + timedelta(hours=1))
    assert "start_time" in error.value.message_dict
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_start_after_end_is_rejected():
    start = timezone.now() + timedelta(days=1)
    with pytest.raises(ValidationError) as error:
        make_event(start_time=start, end_time=start - timedelta(hours=1))
    assert "end_time" in error.value.message_dict


@pytest.mark.django_db
def test_start_equal_to_end_is_rejected():
    start = timezone.now() + timedelta(days=1)
    with pytest.raises(ValidationError):
        make_event(start_time=start, end_time=start)


@pytest.mark.django_db
def test_existing_event_can_be_saved_after_its_start_time_has_passed():
    # The "no past start time" rule only applies when the event is created.
    event = make_event(status=Event.STATUS_SCHEDULED)
    Event.objects.filter(pk=event.pk).update(
        start_time=timezone.now() - timedelta(hours=1)
    )  # .update() skips save(), so we can fake time passing
    event.refresh_from_db()

    event.status = Event.STATUS_IN_PROGRESS
    event.save()  # should not raise
    assert event.status == Event.STATUS_IN_PROGRESS


# ---------- Status transitions ----------

# Every allowed (from, to) pair.
VALID_TRANSITIONS = [
    ("draft", "scheduled"),
    ("draft", "cancelled"),
    ("scheduled", "in_progress"),
    ("scheduled", "cancelled"),
    ("in_progress", "completed"),
]

# A selection of pairs that must be blocked.
INVALID_TRANSITIONS = [
    ("draft", "in_progress"),
    ("draft", "completed"),
    ("scheduled", "draft"),
    ("scheduled", "completed"),
    ("in_progress", "draft"),
    ("in_progress", "scheduled"),
    ("in_progress", "cancelled"),
    ("completed", "draft"),
    ("completed", "scheduled"),
    ("completed", "in_progress"),
    ("completed", "cancelled"),
    ("cancelled", "draft"),
    ("cancelled", "scheduled"),
    ("cancelled", "in_progress"),
    ("cancelled", "completed"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("old_status, new_status", VALID_TRANSITIONS)
def test_valid_status_transitions_are_allowed(old_status, new_status):
    event = make_event(status=old_status)

    event.status = new_status
    event.save()

    event.refresh_from_db()
    assert event.status == new_status


@pytest.mark.django_db
@pytest.mark.parametrize("old_status, new_status", INVALID_TRANSITIONS)
def test_invalid_status_transitions_are_blocked(old_status, new_status):
    event = make_event(status=old_status)

    event.status = new_status
    with pytest.raises(ValidationError) as error:
        event.save()
    assert "status" in error.value.message_dict

    # The database still has the old status.
    event.refresh_from_db()
    assert event.status == old_status


@pytest.mark.django_db
def test_full_lifecycle_draft_to_completed():
    event = make_event()
    for next_status in ["scheduled", "in_progress", "completed"]:
        event.status = next_status
        event.save()
    event.refresh_from_db()
    assert event.status == Event.STATUS_COMPLETED


@pytest.mark.django_db
def test_saving_without_changing_status_is_allowed():
    event = make_event(status=Event.STATUS_COMPLETED)
    event.title = "Renamed"
    event.save()  # same status, so no transition check fails
    event.refresh_from_db()
    assert event.title == "Renamed"


@pytest.mark.django_db
def test_unknown_status_value_is_rejected():
    event = make_event()
    event.status = "not_a_status"
    with pytest.raises(ValidationError):
        event.save()


@pytest.mark.django_db
def test_allowed_next_statuses():
    assert [v for v, _ in make_event(status="draft").allowed_next_statuses()] == [
        "scheduled",
        "cancelled",
    ]
    assert make_event(status="completed").allowed_next_statuses() == []
