# Generated by Django 2.1.1 on 2020-06-20 21:08

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('est', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Import',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('border', django.contrib.gis.db.models.fields.PolygonField(srid=4326)),
                ('active', models.BooleanField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='trailnetwork',
            name='source',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='est.Import'),
            preserve_default=False,
        ),
    ]
