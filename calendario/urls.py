from django.urls import path

from . import views

urlpatterns = [
    path("", views.CalendarView.as_view(), name="calendario"),
    path("eventos/", views.EventListView.as_view(), name="calendario-eventos"),
]
