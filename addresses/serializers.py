from rest_framework import serializers


class AddressSerializer(serializers.Serializer):
    postal_code = serializers.CharField()
    street = serializers.CharField(allow_blank=True)
    complement = serializers.CharField(allow_blank=True)
    neighborhood = serializers.CharField(allow_blank=True)
    city = serializers.CharField()
    state = serializers.CharField()
