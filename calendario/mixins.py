from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse


class LoginRequiredJSONMixin(LoginRequiredMixin):
    """For JSON endpoints: reject unauthenticated requests with 401 instead
    of redirecting to the login page, since these are only ever called via
    fetch(), never navigated to directly."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Debe iniciar sesión."}, status=401)
        return super().dispatch(request, *args, **kwargs)
