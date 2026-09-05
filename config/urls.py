"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("calendario/", include("calendario.urls")),
    path("", TemplateView.as_view(template_name="homemig.html"), name="home"),
    path(
        "noticias/",
        TemplateView.as_view(template_name="noticias.html"),
        name="noticias",
    ),
    path(
        "informacion/telefonos-importantes/",
        TemplateView.as_view(template_name="telefonos-importantes.html"),
        name="telefonos-importantes",
    ),
    path(
        "informacion/basura-y-reciclaje/",
        TemplateView.as_view(template_name="basura-y-reciclaje.html"),
        name="basura-y-reciclaje",
    ),
    path(
        "informacion/desechos-no-tradicionales/",
        TemplateView.as_view(template_name="desechos-no-tradicionales.html"),
        name="desechos-no-tradicionales",
    ),
]
