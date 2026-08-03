from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import SignupForm


class SignupView(CreateView):
    form_class = SignupForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Cuenta creada. Un administrador debe aprobarla antes de que puedas iniciar sesión.',
        )
        return response


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
