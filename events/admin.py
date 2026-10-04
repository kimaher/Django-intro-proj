"""
admin.py - registers Event with the built-in Django admin site (/admin/).

The admin saves through Event.save(), so the same rules apply there too.
"""

from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # Columns shown on the admin list page.
    list_display = ["title", "status", "start_time", "end_time", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "description"]
