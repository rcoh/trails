# Generated by Django 2.1.1 on 2018-09-13 00:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20180912_2228'),
    ]

    operations = [
        migrations.AddField(
            model_name='trailhead',
            name='name',
            field=models.CharField(default='', max_length=32),
            preserve_default=False,
        ),
    ]
