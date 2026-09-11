from django.urls import path

from .views import NoticiaDetalleView, NoticiasListView

urlpatterns = [
    path("", NoticiasListView.as_view(), name="noticias"),
    path("<slug:slug>/", NoticiaDetalleView.as_view(), name="noticias-detalle"),
]
