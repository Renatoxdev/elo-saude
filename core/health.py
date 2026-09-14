from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(exclude=True)
@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def live(request):
    return Response({"status": "ok"})


@extend_schema(exclude=True)
@api_view(["GET", "HEAD"])
@authentication_classes([])
@permission_classes([AllowAny])
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response({"status": "unavailable"}, status=503)
    return Response({"status": "ok"})
