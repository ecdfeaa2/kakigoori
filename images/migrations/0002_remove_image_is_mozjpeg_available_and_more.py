# Generated by Django 5.0 on 2024-04-08 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('images', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='is_mozjpeg_available',
        ),
        migrations.AddField(
            model_name='image',
            name='is_jpegli_available',
            field=models.BooleanField(default=False),
        ),
    ]
