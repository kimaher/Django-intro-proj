"""
exceptions.py - turns model ValidationErrors into clean API responses.

DRF only knows about its own ValidationError. When Event.save() raises
django.core.exceptions.ValidationError, DRF would normally let it crash
into a 500 server error. This handler catches it and returns a 400
instead, with the error messages as JSON. It is switched on in
settings.py (REST_FRAMEWORK["EXCEPTION_HANDLER"]).
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            # Errors tied to fields, e.g. {"end_time": ["End time must be ..."]}
            data = dict(exc.message_dict)
            # Django uses "__all__" for errors not tied to one field.
            # DRF calls these "non_field_errors", so rename for consistency.
            if "__all__" in data:
                data["non_field_errors"] = data.pop("__all__")
        else:
            data = {"non_field_errors": exc.messages}
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    # Anything else: let DRF handle it the normal way.
    return exception_handler(exc, context)
