# Generated by Django 2.2.13 on 2020-07-06 16:11

import django.contrib.gis.db.models.fields
from django.contrib.gis.geos import MultiPoint
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('est', '0009_import_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='trailnetwork',
            name='trailheads',
            field=django.contrib.gis.db.models.fields.MultiPointField(default=MultiPoint(), srid=4326),
            preserve_default=False,
        ),
    ]