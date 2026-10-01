from django.views.generic import TemplateView

from noticias.content import list_articles


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_articles"] = list_articles()[:3]
        return context
