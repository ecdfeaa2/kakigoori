from django.core.management.base import BaseCommand

from images.models import Image, ImageVariant, ImageVariantTask


class Command(BaseCommand):
    def handle(self, *args, **options):
        images = Image.objects.filter(model_version=2).all()
        images_len = len(images)
        for index, image in enumerate(images):
            print(f"Image {index}/{images_len}")
            variants = ImageVariant.objects.filter(image=image).all()
            variant_sizes = list(set(map(lambda x: (x.width, x.height), variants)))

            for image_type in ["avif", "webp", "jpegli"]:
                for variant_size in variant_sizes:
                    avif_variant = [
                        x
                        for x in variants
                        if x.width == variant_size[0]
                        and x.height == variant_size[1]
                        and x.file_type == image_type
                    ]
                    if not avif_variant:
                        ImageVariantTask(
                            image=image,
                            height=variant_size[1],
                            width=variant_size[0],
                            original_file_type=image.imagevariant_set.filter(
                                is_full_size=True, file_type__in=["jpg", "png"]
                            )
                            .first()
                            .file_type,
                            file_type=image_type,
                        ).save()
