# Generated by Django 2.1.1 on 2018-09-21 04:17

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Node',
            fields=[
                ('point', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('osm_id', models.PositiveIntegerField(primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('length_km', models.FloatField()),
                ('elevation_gain', models.FloatField()),
                ('elevation_loss', models.FloatField()),
                ('is_loop', models.BooleanField()),
                ('nodes', django.contrib.gis.db.models.fields.LineStringField(srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='Trailhead',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
                ('node', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='api.Node')),
            ],
        ),
        migrations.CreateModel(
            name='TrailNetwork',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('trail_length_km', models.FloatField()),
                ('unique_id', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='TravelCache',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_point', django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='TravelTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('travel_time_minutes', models.FloatField()),
                ('osm_id', models.PositiveIntegerField()),
                ('start_point', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.TravelCache')),
            ],
        ),
        migrations.AddField(
            model_name='trailhead',
            name='trail_network',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.TrailNetwork'),
        ),
        migrations.AddField(
            model_name='route',
            name='trail_network',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.TrailNetwork'),
        ),
        migrations.AddField(
            model_name='route',
            name='trailhead',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Trailhead'),
        ),
    ]
