from functools import wraps
from typing import Optional

from django.http import JsonResponse, HttpResponseForbidden

from images.models import Image, AuthorizationKey


def get_image(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        image_id = kwargs["image_id"]
        del kwargs["image_id"]
        image = Image.objects.filter(id=image_id).first()
        if image is None:
            return JsonResponse({"error": "Image not found"}, status=404)

        return func(request=request, image=image, *args, **kwargs)

    return wrapper


def can_upload_image(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if "Authorization" not in request.headers:
            return HttpResponseForbidden()

        authorization_key: Optional[AuthorizationKey] = AuthorizationKey.objects.filter(
            id=request.headers["Authorization"], can_upload_image=True
        ).first()

        if not authorization_key:
            return HttpResponseForbidden()

        return func(request, *args, **kwargs)

    return wrapper


def can_upload_variant(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if "Authorization" not in request.headers:
            return HttpResponseForbidden()

        authorization_key: Optional[AuthorizationKey] = AuthorizationKey.objects.filter(
            id=request.headers["Authorization"], can_upload_variant=True
        ).first()

        if not authorization_key:
            return HttpResponseForbidden()

        return func(request, *args, **kwargs)

    return wrapper
