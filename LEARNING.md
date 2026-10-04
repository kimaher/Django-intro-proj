# How a request flows through event_scheduler

This guide follows real requests through the project, file by file. Open the
files side by side as you read.

```
browser ──► event_scheduler/urls.py ──► events/urls.py ──► view function / API view
                                                               │
                                     ┌─────────────────────────┤
                                     ▼                         ▼
                           events/forms.py            events/serializers.py
                           (HTML pages)               (JSON API)
                                     └──────────┬──────────────┘
                                                ▼
                                       events/models.py   ◄── all the rules live here
                                                │
                                                ▼
                                          db.sqlite3
                                                │
                    HTML: events/templates/events/*.html   |   API: JSON response
```

## The project map

| File | Job |
|---|---|
| `event_scheduler/settings.py` | Configuration: installed apps (`rest_framework`, `events`), SQLite database, time zone, and `REST_FRAMEWORK["EXCEPTION_HANDLER"]`. |
| `event_scheduler/urls.py` | The entry point for every URL. Sends `/admin/` to the admin and everything else to `events/urls.py`. |
| `events/urls.py` | Maps each URL in the app to a view, and gives each one a `name`. |
| `events/models.py` | The `Event` table **and every business rule**. |
| `events/forms.py` | `EventForm`, the HTML form for creating events. |
| `events/views.py` | Functions that build the HTML pages. |
| `events/serializers.py` | `EventSerializer`, which converts `Event` ⇄ JSON. |
| `events/api_views.py` | The API endpoints. |
| `events/exceptions.py` | Turns a model `ValidationError` into an HTTP 400 in the API. |
| `events/admin.py` | Registers `Event` in the admin site. |
| `events/templates/events/` | The HTML templates. |
| `events/static/events/style.css` | The CSS. |

---

## Step 0: The rules in `models.py`

Everything else depends on this file, so start here.

`Event` has two class-level dictionaries/lists that describe the rules:

- `STATUS_CHOICES` is the list of valid statuses.
- `ALLOWED_TRANSITIONS` says where each status may go next, for example
  `STATUS_DRAFT: [STATUS_SCHEDULED, STATUS_CANCELLED]`.

There are three methods that enforce them:

1. **`Event.clean()`** checks rules that involve more than one field:
   - a new event (`self.pk is None`) cannot have `start_time` in the past
   - `start_time` must be before `end_time`
   - it calls `check_status_transition()` for the status rule

   If something fails, it raises `ValidationError({"field_name": "message"})`.
2. **`Event.check_status_transition()`** looks up the status that's
   *currently stored in the database* (`Event.objects.filter(pk=self.pk)...`)
   and compares it with the new `self.status` using `ALLOWED_TRANSITIONS`.
3. **`Event.save()`** calls `self.full_clean()` before `super().save()`.
   By default Django **does not** validate on `save()`. Overriding it this way
   means that every save is checked: from a view, the API, the admin, the
   shell, or a test.

`full_clean()` runs `clean_fields()` (required fields, max length, valid
choice), then `clean()`, then `validate_unique()`, and raises one combined
`ValidationError` if anything failed.

There's also a helper the templates use: **`Event.allowed_next_statuses()`**
returns the `(value, label)` pairs for the buttons on the detail page.

> ⚠️ A caveat to know about: `Event.objects.filter(...).update(...)` and
> `bulk_create()` write straight to the database **without** calling
> `save()`, so they skip these rules. This project never uses them except in
> one test, where skipping the rules is the point.

---

## Request 1: `GET /` (the home page)

1. **`event_scheduler/urls.py`**: `path("", include("events.urls"))` passes
   the request on to the app.
2. **`events/urls.py`**: `path("", views.event_list, name="event_list")`
   matches, so Django calls `event_list(request)`.
3. **`events/views.py` → `event_list()`**: runs `Event.objects.all()`. The
   ordering comes from `Event.Meta.ordering = ["start_time"]` in `models.py`.
4. The view calls `render(request, "events/event_list.html", {"events": events})`.
5. **`templates/events/event_list.html`** starts with
   `{% extends "events/base.html" %}`, so it gets the header, nav and CSS from
   `base.html`. It loops `{% for event in events %}`, and shows
   `event.get_status_display` (a method Django creates automatically for
   fields with `choices`, which turns `"in_progress"` into `"In progress"`).
   Links are built with `{% url 'event_detail' event.pk %}`, which uses the
   `name=` from `events/urls.py`, so URLs are never hard-coded.

## Request 2: `GET /events/new/`, then `POST /events/new/` (create an event)

**The GET (showing the empty form):**

1. `events/urls.py` matches `path("events/new/", views.event_create, ...)`.
2. `event_create()` sees `request.method == "GET"` and creates an empty
   `EventForm()`.
3. `templates/events/event_form.html` loops over `{% for field in form %}` and
   prints each input. The `datetime-local` widgets come from
   `EventForm.Meta.widgets` in `forms.py`.

**The POST (submitting the form):**

1. Same URL, same view, but now `request.method == "POST"`.
2. `form = EventForm(request.POST)` fills the form with the submitted data.
3. `form.is_valid()` is where the important part happens. A `ModelForm`:
   - converts the text inputs into Python values (strings to `datetime`)
   - builds an unsaved `Event` instance
   - calls **`Event.full_clean()`**, which runs **`Event.clean()`** in `models.py`
   - copies any `ValidationError` messages onto the form fields
     (`{"start_time": "..."}` ends up on `form["start_time"].errors`)
4. **If it's invalid**, the view falls through to `render(... {"form": form})`.
   The template prints `{% for error in field.errors %}` under each field, so
   the user sees "Start time cannot be in the past." next to the input.
   `forms.py` has no validation code of its own; the message comes from
   `models.py`.
5. **If it's valid**, `form.save()` calls `Event.save()` (which runs
   `full_clean()` once more, as a safety net) and writes the row.
   `messages.success(...)` stores a one-time message, and
   `redirect("event_detail", pk=event.pk)` sends the browser to the new
   event's page.

## Request 3: `GET /events/5/` (the detail page)

1. `events/urls.py`: `path("events/<int:pk>/", views.event_detail, ...)`.
   The `<int:pk>` part captures `5` and passes it as `pk=5`.
2. `event_detail(request, pk)` uses `get_object_or_404(Event, pk=pk)`, which
   returns a 404 page instead of crashing if the event doesn't exist.
3. `templates/events/event_detail.html` calls
   `{% with next_statuses=event.allowed_next_statuses %}`, which runs
   `Event.allowed_next_statuses()` in `models.py`. For a draft event that
   gives Scheduled and Cancelled, so only those two buttons appear. For
   completed or cancelled it's an empty list, so the template shows "can no
   longer change".
4. `base.html` prints any `messages` (like "Event 'X' created.") at the top.

## Request 4: `POST /events/5/status/` (clicking a status button)

1. Each button is `<button name="status" value="scheduled">` inside a form
   that posts to `{% url 'event_change_status' event.pk %}`.
2. `events/urls.py` routes it to `views.event_change_status(request, pk)`.
3. The view sets `event.status = request.POST.get("status", "")` and calls
   `event.save()` inside `try:`.
4. `Event.save()` calls `full_clean()`, which calls `clean()`, which calls
   `check_status_transition()`. That method reads the old status from the
   database and checks it against `ALLOWED_TRANSITIONS`.
5. **Allowed**: the row is saved and `messages.success(...)` runs.
   **Not allowed**: `ValidationError` is raised, and the view's
   `except ValidationError as error:` turns each of `error.messages` into a
   `messages.error(...)`, so nothing crashes.
6. In both cases the view redirects back to the detail page, and `base.html`
   shows the green or red message.

> To see the error path in the browser: open an event in two tabs, click
> "Cancelled" in one, then click "Scheduled" in the other (the stale tab
> still shows the old buttons).

## Request 5: The API, `POST /api/events/`

1. `events/urls.py`:
   `path("api/events/", api_views.EventListCreateAPIView.as_view(), ...)`.
   This view is a class, and `.as_view()` turns it into a function Django
   can call.
2. **`events/api_views.py` → `EventListCreateAPIView`** extends DRF's
   `generics.ListCreateAPIView`. You don't write `get`/`post` yourself:
   - GET serializes `queryset` (all events) into a JSON list
   - POST runs `serializer = EventSerializer(data=request.data)`, then
     `serializer.is_valid()`, then `serializer.save()`
3. **`events/serializers.py` → `EventSerializer`** is a `ModelSerializer`.
   `serializer.is_valid()` only checks the shape of the data (title present,
   dates parse, status is a valid choice). If that fails, DRF itself returns
   a 400. It doesn't know about our business rules.
4. `serializer.save()` calls `Event.objects.create(...)`, which calls
   **`Event.save()`**, which calls `full_clean()`. If the start time is in the
   past, **`django.core.exceptions.ValidationError`** is raised.
5. DRF doesn't recognise Django's `ValidationError`, and on its own this
   would become a 500 error. But `settings.py` sets
   `REST_FRAMEWORK["EXCEPTION_HANDLER"] = "events.exceptions.custom_exception_handler"`.
6. **`events/exceptions.py` → `custom_exception_handler()`** sees the Django
   `ValidationError`, takes `exc.message_dict` (for example
   `{"start_time": ["Start time cannot be in the past."]}`) and returns
   `Response(data, status=400)`.

`PATCH /api/events/5/` works the same way through `EventDetailAPIView`
(`generics.RetrieveUpdateAPIView`). The serializer's `update()` sets the new
attributes and calls `instance.save()`, so an invalid transition such as
draft → completed also comes back as a 400.

You can try the API in your browser at <http://127.0.0.1:8000/api/events/>.
DRF's "browsable API" lets you POST from a form at the bottom of the page.

## Request 6: The admin, `/admin/`

`events/admin.py` registers `Event` with `@admin.register(Event)`. The admin
uses a `ModelForm` internally, so it goes through the same `full_clean()`
and `Event.clean()` as `EventForm`. Invalid changes show red errors there too.

---

## Why put every rule in `models.py`?

There are four ways into the data (web form, status buttons, API, admin),
and all of them end at `Event.save()`. If the rules lived in the views or
serializers, you'd have to copy them into each one, and sooner or later the
copies would drift apart. With the rules in the model, each entry point only
has to do one thing: **show the `ValidationError` nicely**:

| Entry point | How it shows the error |
|---|---|
| `EventForm` (web create) | `ModelForm` attaches it to `field.errors` |
| `event_change_status` (buttons) | `try/except` → `messages.error` |
| API | `custom_exception_handler` → HTTP 400 JSON |
| Admin | Built-in `ModelForm` error display |

## The tests

| File | What it proves |
|---|---|
| `events/tests/test_models.py` | Calls `event.save()` directly: past start time, start ≥ end, every valid transition, and a list of invalid ones (`@pytest.mark.parametrize` runs one test per pair). |
| `events/tests/test_api.py` | Uses DRF's `APIClient` to check that bad data gets a 400 and good data gets a 201 or 200. |
| `events/tests/test_views.py` | Uses Django's test `client` to check that the pages render, that form errors appear, and that invalid status changes show a message instead of crashing. |

`@pytest.mark.django_db` gives a test access to a temporary test database
that is created and destroyed automatically. Your `db.sqlite3` is never
touched.
