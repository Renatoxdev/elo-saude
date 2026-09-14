from django.db import models

from .validators import (
    BRAZILIAN_STATES,
    normalize_phone,
    normalize_postal_code,
    validate_nonblank,
    validate_phone,
    validate_postal_code,
)


class Professional(models.Model):
    social_name = models.CharField(max_length=150, validators=[validate_nonblank])
    profession = models.CharField(max_length=100, validators=[validate_nonblank])
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=32, validators=[validate_phone])
    postal_code = models.CharField(max_length=9, validators=[validate_postal_code])
    street = models.CharField(max_length=200, validators=[validate_nonblank])
    number = models.CharField(max_length=20, validators=[validate_nonblank])
    complement = models.CharField(max_length=150, blank=True)
    neighborhood = models.CharField(max_length=100, validators=[validate_nonblank])
    city = models.CharField(max_length=100, validators=[validate_nonblank])
    state = models.CharField(max_length=2, choices=BRAZILIAN_STATES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["social_name", "id"]

    def clean(self):
        super().clean()
        self.contact_phone = normalize_phone(self.contact_phone)
        self.postal_code = normalize_postal_code(self.postal_code)

    def __str__(self):
        return self.social_name
