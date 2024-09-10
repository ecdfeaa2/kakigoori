import hashlib

from PIL import Image as PILImage
from PIL import JpegImagePlugin
from django.conf import settings
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
)
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from images.decorators import (
    get_image,
    can_upload_variant,
    can_upload_image,
)
from images.models import Image, ImageVariant, ImageVariantTask
from images.utils import get_b2_resource

JpegImagePlugin._getmp = lambda x: None


def index(request):
    return render(request, "index.html")


@csrf_exempt
@can_upload_image
def upload(request):
    file = request.FILES["file"]

    bucket = get_b2_resource()

    file_md5_hash = hashlib.file_digest(file, "md5").hexdigest()
    file.seek(0)

    with PILImage.open(file) as im:
        height, width = (im.height, im.width)

        if im.format == "JPEG":
            file_extension = "jpg"
        elif im.format == "PNG":
            file_extension = "png"
        else:
            return {"created": False, "error": "Uploaded file should be JPEG or PNG"}

    file.seek(0)

    same_md5_image = Image.objects.filter(original_md5=file_md5_hash).first()
    if same_md5_image:
        return {"created": False, "id": same_md5_image.id}

    image = Image(
        original_name=file.name,
        original_mime_type=file.content_type,
        original_md5=file_md5_hash,
        height=height,
        width=width,
        model_version=2,
    )

    image.save()

    bucket.upload_fileobj(
        file, f"{image.backblaze_filepath}/{width}-{height}/image.{file_extension}"
    )

    ImageVariant.objects.get_or_create(
        image=image,
        height=height,
        width=width,
        file_type=file_extension,
        is_full_size=True,
    )

    image.create_variant_tasks(image.width, image.height, file_extension)
    image.uploaded = True
    image.save()

    return JsonResponse({"created": True, "id": image.id})


@can_upload_variant
def image_type_optimization_needed(request, image_type):
    tasks = ImageVariantTask.objects.filter(file_type=image_type).all()

    return JsonResponse(
        {
            "variants": [
                {
                    "image_id": task.image.id,
                    "task_id": task.id,
                    "height": task.height,
                    "width": task.width,
                    "file_type": task.original_file_type,
                }
                for task in tasks
            ]
        }
    )


@csrf_exempt
@can_upload_variant
def upload_variant(request):
    if "task_id" not in request.POST:
        return HttpResponseBadRequest()

    task = ImageVariantTask.objects.filter(id=request.POST["task_id"]).first()

    if not task:
        return HttpResponseNotFound()

    image = task.image
    height = task.height
    width = task.width
    file_type = task.file_type
    file = request.FILES["file"]

    if file_type == "jpegli":
        file_name = "jpegli.jpg"
    else:
        file_name = "image." + file_type

    upload_path = f"{image.backblaze_filepath}/{width}-{height}/{file_name}"

    bucket = get_b2_resource()

    bucket.upload_fileobj(file, upload_path)

    ImageVariant.objects.get_or_create(
        image=image,
        height=height,
        width=width,
        file_type=file_type,
        is_full_size=(height == image.height and width == image.width),
    )

    task.delete()

    return JsonResponse({"status": "ok"})


def image_with_size(request, image, width, height, image_type):
    image_variants = ImageVariant.objects.filter(
        image=image, height=height, width=width
    )
    if image_type != "auto":
        if image_type == "original":
            image_variants = image_variants.filter(file_type__in=["jpg", "png"])
        else:
            image_variants = image_variants.filter(file_type=image_type)

    variants = image_variants.all()

    if not variants:
        if image_type != "auto" and image_type != "original":
            return JsonResponse({"error": "Image version not available"}, status=404)
        else:
            image_variant = image.create_variant(width, height)

            return redirect(
                f"{settings.S3_PUBLIC_BASE_PATH}/{image.backblaze_filepath}/{width}-{height}/image.{image_variant.file_type}"
            )

    if image_type == "auto":
        variants_preferred_order = ["avif", "webp", "jpegli", "jpg", "png"]
    elif image_type == "original":
        variants_preferred_order = ["jpg", "png"]
    else:
        variants_preferred_order = [image_type]

    accept_header = request.headers.get("Accept", default="")

    for file_type in variants_preferred_order:
        if (
            file_type == "avif"
            and image_type == "auto"
            and "image/avif" not in accept_header
        ):
            continue

        if (
            file_type == "webp"
            and image_type == "auto"
            and "image/webp" not in accept_header
        ):
            continue

        variant = [x for x in image_variants if x.file_type == file_type]
        if not variant:
            continue

        variant = variant[0]

        if file_type == "jpegli":
            file_name = "jpegli.jpg"
        else:
            file_name = "image." + file_type

        return redirect(
            f"{settings.S3_PUBLIC_BASE_PATH}/{image.backblaze_filepath}/{variant.width}-{variant.height}/{file_name}"
        )

    return HttpResponseNotFound()


@get_image
def get_image_with_height(request, image, height, image_type):
    if height >= image.height:
        height = image.height
        width = image.width
    else:
        width = int(height * image.width / image.height)

    return image_with_size(request, image, width, height, image_type)


@get_image
def get_image_with_width(request, image, width, image_type):
    if width >= image.width:
        width = image.width
        height = image.height
    else:
        height = int(width * image.height / image.width)

    return image_with_size(request, image, width, height, image_type)


@get_image
def get(request, image, image_type):
    return image_with_size(request, image, image.width, image.height, image_type)


@get_image
def get_thumbnail(request, image, image_type):
    width, height = image.thumbnail_size

    return image_with_size(request, image, width, height, image_type)
