"""
api_views.py - the JSON API endpoints (Django REST Framework).

DRF's generic views do the heavy lifting:
  - EventListCreateAPIView: GET lists events, POST creates one
  - EventDetailAPIView:     GET shows one event, PUT/PATCH updates it
Creating and updating both call serializer.save(), which calls Event.save().
"""

from rest_framework import generics

from .models import Event
from .serializers import EventSerializer


class EventListCreateAPIView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
