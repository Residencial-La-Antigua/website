import datetime
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.generic import TemplateView

from .forms import EventForm, RecurrenceForm
from .mixins import LoginRequiredJSONMixin, StaffRequiredJSONMixin
from .models import Event
from .recurrence import (
    MAX_OCCURRENCES,
    TooManyOccurrences,
    generate_occurrence_starts,
)


def serialize_event(event):
    return {
        "id": event.id,
        "title": event.title,
        "start": event.start_at.isoformat(),
        "end": event.end_at.isoformat() if event.end_at else None,
        "extendedProps": {
            "description": event.description,
            "location": event.location,
            "recurringGroup": str(event.recurring_group)
            if event.recurring_group
            else None,
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

        events = Event.objects.filter(start_at__lt=end).filter(
            Q(end_at__gt=start) | Q(end_at__isnull=True, start_at__gte=start)
        )

        return JsonResponse(
            [serialize_event(event) for event in events], safe=False
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
            return JsonResponse(serialize_event(event), status=201)

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
                start_at=occurrence_start,
                end_at=occurrence_start + duration if duration else None,
                recurring_group=group,
                created_by=request.user,
            )
            for occurrence_start in occurrence_starts
        ]
        Event.objects.bulk_create(events)

        return JsonResponse(
            [serialize_event(event) for event in events],
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
        return JsonResponse(serialize_event(event))


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
