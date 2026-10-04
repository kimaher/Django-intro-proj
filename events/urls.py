"""
urls.py (app) - maps URLs to the views in this app.

The project's event_scheduler/urls.py includes this file.
The "name" of each path lets templates and views refer to it,
e.g. {% url 'event_detail' event.pk %} or redirect("event_list").
"""

from django.urls import path

from . import api_views, views

urlpatterns = [
    # HTML pages
    path("", views.event_list, name="event_list"),
    path("events/new/", views.event_create, name="event_create"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("events/<int:pk>/status/", views.event_change_status, name="event_change_status"),
    # JSON API
    path("api/events/", api_views.EventListCreateAPIView.as_view(), name="api_event_list"),
    path("api/events/<int:pk>/", api_views.EventDetailAPIView.as_view(), name="api_event_detail"),
]
