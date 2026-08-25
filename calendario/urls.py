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
        "eventos/<int:pk>/editar/",
        views.EventUpdateView.as_view(),
        name="calendario-eventos-editar",
    ),
    path(
        "eventos/<int:pk>/eliminar/",
        views.EventDeleteView.as_view(),
        name="calendario-eventos-eliminar",
    ),
    path(
        "eventos/<int:pk>/eliminar-serie/",
        views.EventDeleteSeriesView.as_view(),
        name="calendario-eventos-eliminar-serie",
    ),
    path(
        "eventos/<int:pk>/confirmar/",
        views.EventConfirmView.as_view(),
        name="calendario-eventos-confirmar",
    ),
]
