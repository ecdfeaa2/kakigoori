import uuid
from io import BytesIO

from django.db import models
from django.utils import timezone

from images.utils import get_b2_resource
from PIL import Image as PILImage, ImageOps


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creation_date = models.DateTimeField(default=timezone.now)
    uploaded = models.BooleanField(default=False)
    original_name = models.CharField(max_length=150)
    original_mime_type = models.CharField(max_length=10)
    original_md5 = models.CharField(max_length=32)
    is_webp_available = models.BooleanField(default=False)
    is_avif_available = models.BooleanField(default=False)
    is_jpegli_available = models.BooleanField(default=False)
    model_version = models.IntegerField(default=1)
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)

    @property
    def thumbnail_size(self):
        if self.height > self.width:
            return int(600 * self.width / self.height), 600
        else:
            return 600, int(600 * self.height / self.width)

    @property
    def backblaze_filepath(self):
        return f"{self.id.hex[:2]}/{self.id.hex[2:4]}/{self.id.hex}"

    def create_variant_tasks(self, width, height, original_file_type):
        ImageVariantTask(
            image=self,
            height=height,
            width=width,
            original_file_type=original_file_type,
            file_type="avif",
        ).save()

        ImageVariantTask(
            image=self,
            height=height,
            width=width,
            original_file_type=original_file_type,
            file_type="webp",
        ).save()

        ImageVariantTask(
            image=self,
            height=height,
            width=width,
            original_file_type=original_file_type,
            file_type="jpegli",
        ).save()

    def create_variant(self, width, height):
        bucket = get_b2_resource()

        original_image = BytesIO()
        original_variant = self.imagevariant_set.filter(
            is_full_size=True, file_type__in=["jpg", "png"]
        ).first()
        bucket.download_fileobj(
            f"{self.backblaze_filepath}/{original_variant.width}-{original_variant.height}/image.{original_variant.file_type}",
            original_image,
        )
        original_image.seek(0)

        resized_image = BytesIO()

        file_extension = "jpg"

        with PILImage.open(original_image) as im:
            ImageOps.exif_transpose(im, in_place=True)
            im.thumbnail((width, height))

            if im.has_transparency_data:
                try:
                    im.save(resized_image, "PNG")
                    file_extension = "png"
                except OSError:
                    im.convert("RGB").save(resized_image, "JPEG")
            else:
                try:
                    im.save(resized_image, "JPEG")
                except OSError:
                    im.convert("RGB").save(resized_image, "JPEG")

        resized_image.seek(0)

        bucket.upload_fileobj(
            resized_image,
            f"{self.backblaze_filepath}/{width}-{height}/image.{file_extension}",
        )

        image_variant = ImageVariant(
            image=self,
            height=height,
            width=width,
            is_full_size=False,
            file_type=file_extension,
        )

        image_variant.save()

        self.create_variant_tasks(width, height, file_extension)

        return image_variant


class ImageVariant(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    height = models.IntegerField()
    width = models.IntegerField()
    is_full_size = models.BooleanField(default=False)
    file_type = models.CharField(max_length=10)


class ImageVariantTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    height = models.IntegerField()
    width = models.IntegerField()
    original_file_type = models.CharField(max_length=10)
    file_type = models.CharField(max_length=10)


class AuthorizationKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    can_upload_image = models.BooleanField(default=False)
    can_upload_variant = models.BooleanField(default=False)
