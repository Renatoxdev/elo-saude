from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.urls import include, path
from rest_framework.views import APIView


class FailingView(APIView):
    def get(self, request):
        raise RuntimeError("sensitive-internal-value")


def failing_django_view(request):
    raise RuntimeError("sensitive-internal-value")


def django_error_view(request, kind):
    raise {"400": SuspiciousOperation, "403": PermissionDenied, "404": Http404}[kind](
        "sensitive-internal-value"
    )


urlpatterns = [
    path("api/error/<str:kind>/", django_error_view),
    path("api/failure/", FailingView.as_view()),
    path("api/django-failure/", failing_django_view),
    path("", include("config.urls")),
]
