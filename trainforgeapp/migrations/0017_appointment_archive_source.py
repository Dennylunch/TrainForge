from django.db import migrations, models


def mark_existing_archived_appointments_as_legacy(apps, schema_editor):
    Appointment = apps.get_model("trainforgeapp", "Appointment")
    Appointment.objects.filter(is_archived=True).update(archive_source="legacy")


def clear_legacy_archive_source(apps, schema_editor):
    Appointment = apps.get_model("trainforgeapp", "Appointment")
    Appointment.objects.filter(archive_source="legacy").update(archive_source=None)


class Migration(migrations.Migration):

    dependencies = [
        ("trainforgeapp", "0016_default_exercises"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="archive_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("auto", "Automatically archived"),
                    ("manual", "Manually archived"),
                    ("legacy", "Legacy archived"),
                ],
                max_length=10,
                null=True,
            ),
        ),
        migrations.RunPython(
            mark_existing_archived_appointments_as_legacy,
            clear_legacy_archive_source,
        ),
    ]
