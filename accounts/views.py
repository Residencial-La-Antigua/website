from typing import cast

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import ProfileForm, SignupForm


class SignupView(CreateView):
    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Cuenta creada. Un administrador debe aprobarla antes de que puedas iniciar sesión.",
        )
        return response


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        return cast(User, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        password_form = PasswordChangeForm(user=cast(User, self.request.user))
        password_form.fields["old_password"].widget.attrs.pop("autofocus", None)
        context.setdefault("password_form", password_form)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Información de la cuenta actualizada.")
        return response


class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("profile")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # PasswordChangeForm autofocuses this field, which assumes the form is
        # the only thing on the page; here it fights the page's own
        # scroll-to-top-on-render behavior by yanking focus down to this card.
        form.fields["old_password"].widget.attrs.pop("autofocus", None)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["password_form"] = context.pop("form")
        context["form"] = ProfileForm(instance=cast(User, self.request.user))
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Contraseña actualizada.")
        return response
