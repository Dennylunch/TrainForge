from datetime import time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Appointment, Client, UserDetail


class AppointmentCalendarTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.trainer_user = User.objects.create_user(username="trainer", password="password")
        self.trainer = UserDetail.objects.create(user=self.trainer_user, role="trainer")
        self.client_record = self.create_client(self.trainer, "Alex", "Active")
        self.client.force_login(self.trainer_user)

    def create_client(self, trainer, first_name, last_name):
        return Client.objects.create(
            user=trainer,
            first_name=first_name,
            last_name=last_name,
            email=f"{first_name.lower()}.{last_name.lower()}@example.com",
            goal="Strength",
        )

    def create_appointment(self, client, appointment_date, hour=10, **kwargs):
        return Appointment.objects.create(
            client=client,
            date=appointment_date,
            starting_time=time(hour, 0),
            **kwargs,
        )

    def schedule_url(self, appointment_date):
        week_start = appointment_date - timedelta(days=appointment_date.weekday())
        return f"{reverse('schedule')}?week={week_start.isoformat()}"

    def test_past_appointments_are_auto_archived_and_only_auto_history_is_displayed(self):
        past_date = self.today - timedelta(days=3)
        automatic = self.create_appointment(self.client_record, past_date)
        manual_client = self.create_client(self.trainer, "Mia", "Manual")
        legacy_client = self.create_client(self.trainer, "Lee", "Legacy")
        self.create_appointment(
            manual_client,
            past_date,
            is_archived=True,
            archive_source=Appointment.ARCHIVE_SOURCE_MANUAL,
        )
        self.create_appointment(
            legacy_client,
            past_date,
            is_archived=True,
            archive_source=Appointment.ARCHIVE_SOURCE_LEGACY,
        )

        response = self.client.get(self.schedule_url(past_date))

        automatic.refresh_from_db()
        self.assertTrue(automatic.is_archived)
        self.assertEqual(automatic.archive_source, Appointment.ARCHIVE_SOURCE_AUTO)
        self.assertContains(response, "Alex Active")
        self.assertNotContains(response, "Mia Manual")
        self.assertNotContains(response, "Lee Legacy")
        self.assertNotContains(response, reverse("archive_appointment", args=[automatic.pk]))

    def test_manual_archive_stays_hidden_after_its_date_has_passed(self):
        future_date = self.today + timedelta(days=7)
        appointment = self.create_appointment(self.client_record, future_date)

        response = self.client.post(
            f"{reverse('archive_appointment', args=[appointment.pk])}?week={future_date.isoformat()}"
        )

        self.assertRedirects(response, self.schedule_url(future_date))
        appointment.refresh_from_db()
        self.assertTrue(appointment.is_archived)
        self.assertEqual(appointment.archive_source, Appointment.ARCHIVE_SOURCE_MANUAL)

        past_date = self.today - timedelta(days=2)
        appointment.date = past_date
        appointment.save(update_fields=["date"])
        response = self.client.get(self.schedule_url(past_date))
        self.assertNotContains(response, "Alex Active")

    def test_past_appointments_cannot_be_archived_manually(self):
        past_appointment = self.create_appointment(self.client_record, self.today - timedelta(days=1))
        archive_url = reverse('archive_appointment', args=[past_appointment.pk])

        self.assertEqual(self.client.get(archive_url).status_code, 405)
        self.assertEqual(self.client.post(archive_url).status_code, 404)
        past_appointment.refresh_from_db()
        self.assertFalse(past_appointment.is_archived)

    def test_clients_summary_prefers_upcoming_then_auto_history(self):
        past_appointment = self.create_appointment(
            self.client_record,
            self.today - timedelta(days=2),
            is_archived=True,
            archive_source=Appointment.ARCHIVE_SOURCE_AUTO,
        )
        upcoming_appointment = self.create_appointment(self.client_record, self.today + timedelta(days=2))

        response = self.client.get(reverse('all_clients'))
        client_from_context = next(client for client in response.context["clients"] if client.pk == self.client_record.pk)
        self.assertEqual(client_from_context.latest_appointment.pk, upcoming_appointment.pk)

        upcoming_appointment.is_archived = True
        upcoming_appointment.archive_source = Appointment.ARCHIVE_SOURCE_MANUAL
        upcoming_appointment.save(update_fields=["is_archived", "archive_source"])
        response = self.client.get(reverse('all_clients'))
        client_from_context = next(client for client in response.context["clients"] if client.pk == self.client_record.pk)
        self.assertEqual(client_from_context.latest_appointment.pk, past_appointment.pk)

    def test_other_trainers_cannot_archive_an_appointment(self):
        other_user = User.objects.create_user(username="other", password="password")
        other_trainer = UserDetail.objects.create(user=other_user, role="trainer")
        other_client = self.create_client(other_trainer, "Taylor", "Other")
        other_appointment = self.create_appointment(other_client, self.today + timedelta(days=1))

        response = self.client.post(reverse('archive_appointment', args=[other_appointment.pk]))

        self.assertEqual(response.status_code, 404)
        other_appointment.refresh_from_db()
        self.assertFalse(other_appointment.is_archived)
