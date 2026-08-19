from django.urls import path

from . import views

urlpatterns = [
    path("", views.CalendarView.as_view(), name="calendario"),
    path("eventos/", views.EventListView.as_view(), name="calendario-eventos"),
    path(
        "eventos/crear/",
        views.EventCreateView.as_view(),
        name="calendario-eventos-crear",
    ),
    path(
        "eventos/<int:pk>/eliminar/",
        views.EventDeleteView.as_view(),
        name="calendario-eventos-eliminar",
    ),
]
