from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import SimpleRouter

from addresses.views import PostalCodeView
from appointments.views import AppointmentViewSet
from core.auth import LoginView, RefreshView, RevokeView
from core.health import live, ready
from professionals.views import ProfessionalViewSet

router = SimpleRouter()
router.register("professionals", ProfessionalViewSet, basename="professional")
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = [
    path("health/live/", live, name="health-live"),
    path("health/ready/", ready, name="health-ready"),
    path("api/schema/", SpectacularJSONAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api/v1/auth/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", RefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/token/revoke/", RevokeView.as_view(), name="token_revoke"),
    path("api/v1/addresses/<str:postal_code>/", PostalCodeView.as_view(), name="postal_code"),
]
