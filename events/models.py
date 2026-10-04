"""
models.py - defines the database tables for the events app.

The Event model is the single source of truth for ALL business rules:
  - start_time cannot be in the past when an event is created
  - start_time must be before end_time
  - only certain status changes are allowed

Views, forms, serializers and the admin never re-implement these rules.
They just call save() (directly or indirectly) and react to the
ValidationError that the model raises.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Event(models.Model):
    # The possible values for the "status" field.
    # Each pair is (value stored in the database, label shown to humans).
    STATUS_DRAFT = "draft"
    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    # Which statuses each status is allowed to move to.
    # Completed and cancelled map to an empty list: they can never change.
    ALLOWED_TRANSITIONS = {
        STATUS_DRAFT: [STATUS_SCHEDULED, STATUS_CANCELLED],
        STATUS_SCHEDULED: [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS: [STATUS_COMPLETED],
        STATUS_COMPLETED: [],
        STATUS_CANCELLED: [],
    }

    # --- Database columns ---
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    # auto_now_add fills this in automatically when the row is first created.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Show the soonest events first.
        ordering = ["start_time"]

    def __str__(self):
        return self.title

    def allowed_next_statuses(self):
        """Return the (value, label) pairs this event may move to next.

        The detail page uses this to decide which buttons to show.
        """
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, [])
        return [(value, label) for value, label in self.STATUS_CHOICES if value in allowed]

    def clean(self):
        """Check rules that involve more than one field.

        Django calls clean() as part of full_clean(). Errors are raised as a
        dict so each message is attached to the field it belongs to.
        """
        errors = {}

        # Rule 1: a NEW event cannot start in the past.
        # self.pk is None means this event has not been saved to the database yet.
        if self.pk is None and self.start_time and self.start_time < timezone.now():
            errors["start_time"] = "Start time cannot be in the past."

        # Rule 2: the event must start before it ends.
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["end_time"] = "End time must be after the start time."

        # Rule 3: only allowed status changes.
        transition_error = self.check_status_transition()
        if transition_error:
            errors["status"] = transition_error

        if errors:
            raise ValidationError(errors)

    def check_status_transition(self):
        """Return an error message if the status change is not allowed, else None."""
        # A brand-new event has no previous status, so there is nothing to check.
        if self.pk is None:
            return None

        # Look up the status that is currently stored in the database.
        old_status = Event.objects.filter(pk=self.pk).values_list("status", flat=True).first()
        if old_status is None or old_status == self.status:
            return None  # Row not found, or the status is not changing.

        if self.status not in self.ALLOWED_TRANSITIONS.get(old_status, []):
            return f"Cannot change status from '{old_status}' to '{self.status}'."
        return None

    def save(self, *args, **kwargs):
        """Validate everything before writing to the database.

        Django does NOT call full_clean() on save() by default. We call it here
        so the rules are enforced no matter where save() is called from:
        web views, the API, the admin, the shell, or tests.

        full_clean() runs:
          1. clean_fields() - per-field checks (required, max_length, valid choice...)
          2. clean()        - our custom rules above, including status transitions
          3. validate_unique()
        and raises ValidationError if anything is wrong.
        """
        self.full_clean()
        super().save(*args, **kwargs)
