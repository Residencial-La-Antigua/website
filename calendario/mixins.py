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


class StaffRequiredJSONMixin(LoginRequiredJSONMixin):
    """Like LoginRequiredJSONMixin, but also rejects authenticated
    non-staff users with 403 instead of letting the view run."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            return JsonResponse({"detail": "No autorizado."}, status=403)
        return super().dispatch(request, *args, **kwargs)
