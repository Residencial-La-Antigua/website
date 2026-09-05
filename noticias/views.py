from django.http import Http404
from django.views.generic import TemplateView

from .content import get_article, list_articles


class NoticiasListView(TemplateView):
    template_name = "noticias/lista.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["articles"] = list_articles()
        return context


class NoticiaDetalleView(TemplateView):
    template_name = "noticias/detalle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = get_article(kwargs["slug"])
        if article is None:
            raise Http404("Noticia no encontrada.")
        context["article"] = article
        return context
