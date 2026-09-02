import datetime
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.generic import TemplateView

from .forms import EventForm, RecurrenceForm
from .ics import build_event_ics
from .mixins import LoginRequiredJSONMixin, StaffRequiredJSONMixin
from .models import Confirmation, Event
from .recurrence import (
    MAX_OCCURRENCES,
    TooManyOccurrences,
    generate_occurrence_starts,
)


def serialize_event(event, is_confirmed, confirmed_count):
    return {
        "id": event.id,
        "title": event.title,
        "start": event.start_at.isoformat(),
        "end": event.end_at.isoformat() if event.end_at else None,
        "extendedProps": {
            "description": event.description,
            "location": event.location,
            "meetingLink": event.meeting_link,
            "recurringGroup": str(event.recurring_group)
            if event.recurring_group
            else None,
            "confirmed": is_confirmed,
            "confirmedCount": confirmed_count,
        },
    }


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = "calendario/calendario.html"


class EventListView(LoginRequiredJSONMixin, View):
    """Returns, as JSON, the events whose ``start``/``end`` range (query
    params, ISO 8601) overlaps the requested window. Defaults to the
    current month when no range is given."""

    def get(self, request):
        start = self._parse_param(request.GET.get("start"))
        end = self._parse_param(request.GET.get("end"))
        if start is None or end is None:
            start, end = self._current_month_range()

        events = list(
            Event.objects.filter(start_at__lt=end)
            .filter(
                Q(end_at__gt=start)
                | Q(end_at__isnull=True, start_at__gte=start)
            )
            .annotate(confirmed_count=Count("confirmations"))
        )
        confirmed_ids = set(
            Confirmation.objects.filter(
                user=request.user, event__in=events
            ).values_list("event_id", flat=True)
        )

        return JsonResponse(
            [
                serialize_event(
                    event, event.id in confirmed_ids, event.confirmed_count
                )
                for event in events
            ],
            safe=False,
        )

    @staticmethod
    def _parse_param(value):
        if not value:
            return None
        dt = parse_datetime(value)
        if dt is None:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, datetime.UTC)
        return dt

    @staticmethod
    def _current_month_range():
        today = timezone.now().date()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        return (
            timezone.make_aware(
                datetime.datetime.combine(month_start, datetime.time.min),
                datetime.UTC,
            ),
            timezone.make_aware(
                datetime.datetime.combine(month_end, datetime.time.min),
                datetime.UTC,
            ),
        )


class EventCreateView(StaffRequiredJSONMixin, View):
    def post(self, request):
        form = EventForm(request.POST)
        recurrence_form = RecurrenceForm(request.POST)

        if not form.is_valid() or not recurrence_form.is_valid():
            errors = form.errors.get_json_data()
            errors.update(recurrence_form.errors.get_json_data())
            return JsonResponse({"errors": errors}, status=400)

        if not recurrence_form.cleaned_data["is_recurring"]:
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            return JsonResponse(serialize_event(event, False, 0), status=201)

        try:
            occurrence_starts = generate_occurrence_starts(
                form.cleaned_data["start_at"],
                recurrence_form.cleaned_data["frequency"],
                end_date=recurrence_form.cleaned_data["end_date"],
                occurrence_count=recurrence_form.cleaned_data[
                    "occurrence_count"
                ],
            )
        except TooManyOccurrences:
            message = (
                f"El rango genera demasiadas ocurrencias (máximo "
                f"{MAX_OCCURRENCES}). Favor de reducir la fecha final."
            )
            return JsonResponse(
                {
                    "errors": {
                        "end_date": [
                            {
                                "message": message,
                                "code": "too_many_occurrences",
                            }
                        ]
                    }
                },
                status=400,
            )

        duration = None
        if form.cleaned_data["end_at"]:
            duration = (
                form.cleaned_data["end_at"] - form.cleaned_data["start_at"]
            )

        group = uuid.uuid4()
        events = [
            Event(
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                location=form.cleaned_data["location"],
                meeting_link=form.cleaned_data["meeting_link"],
                start_at=occurrence_start,
                end_at=occurrence_start + duration if duration else None,
                recurring_group=group,
                created_by=request.user,
            )
            for occurrence_start in occurrence_starts
        ]
        Event.objects.bulk_create(events)

        return JsonResponse(
            [serialize_event(event, False, 0) for event in events],
            safe=False,
            status=201,
        )


class EventUpdateView(StaffRequiredJSONMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        form = EventForm(request.POST, instance=event)
        if not form.is_valid():
            return JsonResponse(
                {"errors": form.errors.get_json_data()}, status=400
            )

        form.save()
        is_confirmed = event.confirmations.filter(user=request.user).exists()
        return JsonResponse(
            serialize_event(event, is_confirmed, event.confirmations.count())
        )


class EventDeleteView(StaffRequiredJSONMixin, View):
    def delete(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        event.delete()
        return HttpResponse(status=204)


class EventDeleteSeriesView(StaffRequiredJSONMixin, View):
    """Deletes this occurrence and every later one (by start_at) sharing
    its recurring_group. Past occurrences in the same series, and events
    outside the series, are untouched."""

    def delete(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.recurring_group is None:
            event.delete()
        else:
            Event.objects.filter(
                recurring_group=event.recurring_group,
                start_at__gte=event.start_at,
            ).delete()
        return HttpResponse(status=204)


class EventConfirmView(LoginRequiredJSONMixin, View):
    """Toggles the requesting user's attendance confirmation for an event.
    Open to any authenticated resident, not just staff. Both directions
    are idempotent: confirming twice or cancelling a confirmation that
    doesn't exist both succeed without error."""

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        Confirmation.objects.get_or_create(user=request.user, event=event)
        return JsonResponse(
            serialize_event(event, True, event.confirmations.count())
        )

    def delete(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        Confirmation.objects.filter(user=request.user, event=event).delete()
        return HttpResponse(status=204)


class EventIcsView(LoginRequiredMixin, View):
    """Downloads a single event (or, for a recurring series, this one
    occurrence) as an .ics file, for import into Outlook or other
    calendar apps."""

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        response = HttpResponse(
            build_event_ics(event), content_type="text/calendar; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="evento-{event.pk}.ics"'
        )
        return response
