"""
serializers.py - converts Event objects to/from JSON for the API.

A ModelSerializer builds its fields from the Event model. It only handles
the basic shape of the data (types, required fields). The real business
rules live in Event.clean()/save(); if they fail, the ValidationError is
turned into a 400 response by events/exceptions.py.
"""

from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "description", "start_time", "end_time", "status", "created_at"]
        # The client cannot set these; the database fills them in.
        read_only_fields = ["id", "created_at"]
