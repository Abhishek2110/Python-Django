# Generated by Django 5.0.2 on 2024-02-27 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Notes', '0006_alter_notes_reminder'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notes',
            name='reminder',
            field=models.DateTimeField(null=True),
        ),
    ]