def professional_payload(**overrides):
    return {
        "social_name": "Alex",
        "profession": "Psicologia",
        "contact_email": "alex@example.test",
        "contact_phone": "+5511912345678",
        "postal_code": "01001000",
        "street": "Praça da Sé",
        "number": "s/n",
        "complement": "",
        "neighborhood": "Sé",
        "city": "São Paulo",
        "state": "SP",
        **overrides,
    }
