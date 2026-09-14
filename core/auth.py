from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)


class LoginView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema_view(post=extend_schema(responses={200: {"type": "object", "properties": {}}}))
class RevokeView(TokenBlacklistView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"
