import sys
from io import BytesIO
from PIL import Image as PILImage


import boto3
from botocore.config import Config
from django.core.management.base import BaseCommand, CommandError

from images.models import Image, ImageVariant


class Command(BaseCommand):
    def get_b2_resource(self, endpoint, key_id, application_key):
        b2 = boto3.resource(
            service_name="s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=application_key,
            config=Config(signature_version="s3v4"),
        )

        bucket = b2.Bucket("kakigoori")

        return bucket

    def handle(self, *args, **options):
        images = Image.objects.filter(model_version=1).order_by("-creation_date").all()
        images_len = len(images)
        progress = 1
        print(f"{images_len} images found")
        for image in images:
            print(f"Image {progress}/{images_len}")
            try:
                print("Upgrading image %s" % image.id)

                bucket = self.get_b2_resource(
                    "https://s3.eu-central-003.backblazeb2.com",
                    "0032dcec6092f3e0000000021",
                    "K0039Xb1GE/An9P1ccK2B+19pXrKnnU",
                )

                print("Getting original image...")

                original_image = BytesIO()
                bucket.download_fileobj(
                    f"{image.backblaze_filepath}/original.jpg", original_image
                )
                original_image.seek(0)

                with PILImage.open(original_image) as im:
                    image.height = im.height
                    image.width = im.width
                    image.save()

                print("Copying original images...")

                bucket.copy(
                    {
                        "Bucket": "kakigoori",
                        "Key": f"{image.backblaze_filepath}/original.jpg",
                    },
                    f"{image.backblaze_filepath}/{image.width}-{image.height}/image.jpg",
                )
                bucket.copy(
                    {
                        "Bucket": "kakigoori",
                        "Key": f"{image.backblaze_filepath}/thumbnail.jpg",
                    },
                    f"{image.backblaze_filepath}/{image.thumbnail_size[0]}-{image.thumbnail_size[1]}/image.jpg",
                )

                delete_objects_list = [f"{image.backblaze_filepath}/thumbnail.jpg"]

                ImageVariant(
                    image=image,
                    height=image.height,
                    width=image.width,
                    is_full_size=True,
                    file_type="jpg",
                ).save()
                ImageVariant(
                    image=image,
                    height=image.thumbnail_size[1],
                    width=image.thumbnail_size[0],
                    is_full_size=False,
                    file_type="jpg",
                ).save()

                if image.is_jpegli_available:
                    print("Copying JPEGLI images...")
                    bucket.copy(
                        {
                            "Bucket": "kakigoori",
                            "Key": f"{image.backblaze_filepath}/jpegli.jpg",
                        },
                        f"{image.backblaze_filepath}/{image.width}-{image.height}/jpegli.jpg",
                    )
                    bucket.copy(
                        {
                            "Bucket": "kakigoori",
                            "Key": f"{image.backblaze_filepath}/thumbnail_jpegli.jpg",
                        },
                        f"{image.backblaze_filepath}/{image.thumbnail_size[0]}-{image.thumbnail_size[1]}/jpegli.jpg",
                    )

                    ImageVariant(
                        image=image,
                        height=image.height,
                        width=image.width,
                        is_full_size=True,
                        file_type="jpegli",
                    ).save()
                    ImageVariant(
                        image=image,
                        height=image.thumbnail_size[0],
                        width=image.thumbnail_size[1],
                        is_full_size=False,
                        file_type="jpegli",
                    ).save()

                    delete_objects_list += [
                        f"{image.backblaze_filepath}/jpegli.jpg",
                        f"{image.backblaze_filepath}/thumbnail_jpegli.jpg",
                    ]
                if image.is_avif_available:
                    print("Copying AVIF images...")
                    bucket.copy(
                        {
                            "Bucket": "kakigoori",
                            "Key": f"{image.backblaze_filepath}/optimized.avif",
                        },
                        f"{image.backblaze_filepath}/{image.width}-{image.height}/image.avif",
                    )
                    bucket.copy(
                        {
                            "Bucket": "kakigoori",
                            "Key": f"{image.backblaze_filepath}/thumbnail.avif",
                        },
                        f"{image.backblaze_filepath}/{image.thumbnail_size[0]}-{image.thumbnail_size[1]}/image.avif",
                    )

                    ImageVariant(
                        image=image,
                        height=image.height,
                        width=image.width,
                        is_full_size=True,
                        file_type="avif",
                    ).save()
                    ImageVariant(
                        image=image,
                        height=image.thumbnail_size[0],
                        width=image.thumbnail_size[1],
                        is_full_size=False,
                        file_type="avif",
                    ).save()

                    delete_objects_list += [
                        f"{image.backblaze_filepath}/optimized.avif",
                        f"{image.backblaze_filepath}/thumbnail.avif",
                    ]
                if image.is_webp_available:
                    print("Copying WebP images...")
                    bucket.copy(
                        {
                            "Bucket": "kakigoori",
                            "Key": f"{image.backblaze_filepath}/optimized.webp",
                        },
                        f"{image.backblaze_filepath}/{image.width}-{image.height}/image.webp",
                    )
                    bucket.copy(
                        {
                            "Bucket": "kakigoori",
                            "Key": f"{image.backblaze_filepath}/thumbnail.webp",
                        },
                        f"{image.backblaze_filepath}/{image.thumbnail_size[0]}-{image.thumbnail_size[1]}/image.webp",
                    )

                    ImageVariant(
                        image=image,
                        height=image.height,
                        width=image.width,
                        is_full_size=True,
                        file_type="webp",
                    ).save()
                    ImageVariant(
                        image=image,
                        height=image.thumbnail_size[0],
                        width=image.thumbnail_size[1],
                        is_full_size=False,
                        file_type="webp",
                    ).save()

                    delete_objects_list += [
                        f"{image.backblaze_filepath}/optimized.webp",
                        f"{image.backblaze_filepath}/thumbnail.webp",
                    ]

                print("Saving...")

                image.model_version = 2
                image.save()

                print("Deleting old files...")

                bucket.delete_objects(
                    Delete={"Objects": [{"Key": x} for x in delete_objects_list]}
                )

                progress += 1
            except KeyboardInterrupt:
                sys.exit(1)
            except:
                progress += 1
                pass
