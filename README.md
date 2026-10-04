# Django-intro-proj
Small event scheduler built with Django, Django REST Framework, and SQLite.

See [LEARNING.md](LEARNING.md) for a walkthrough of how a request flows through the code.

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000/ (site), http://127.0.0.1:8000/api/events/ (API), http://127.0.0.1:8000/admin/ (admin).

## Tests

```powershell
pytest
```
