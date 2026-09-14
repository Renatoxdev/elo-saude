from rest_framework import serializers


class StrictModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {field: ["Campo desconhecido."] for field in sorted(unknown)}
                )
        return super().to_internal_value(data)
