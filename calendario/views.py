import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.generic import TemplateView

from .forms import EventForm
from .mixins import LoginRequiredJSONMixin, StaffRequiredJSONMixin
from .models import Event


def serialize_event(event):
    return {
        "id": event.id,
        "title": event.title,
        "start": event.start_at.isoformat(),
        "end": event.end_at.isoformat() if event.end_at else None,
        "extendedProps": {
            "description": event.description,
            "location": event.location,
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
        if not form.is_valid():
            return JsonResponse(
                {"errors": form.errors.get_json_data()}, status=400
            )

        event = form.save(commit=False)
        event.created_by = request.user
        event.save()

        return JsonResponse(serialize_event(event), status=201)
