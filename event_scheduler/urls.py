"""
urls.py (project) - the first place Django looks when a request comes in.

It sends /admin/ to the Django admin, and everything else to the
events app's own urls.py (events/urls.py).
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("events.urls")),
]
