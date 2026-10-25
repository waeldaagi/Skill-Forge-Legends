from payments.models import Plan

DEMO_PLANS = [
    {
        "slug": "gratuit",
        "name": "Gratuit",
        "price": "0.000",
        "duration_days": 365,
        "benefits": "Accès aux cours gratuits",
    },
    {
        "slug": "premium",
        "name": "Premium",
        "price": "29.900",
        "duration_days": 30,
        "benefits": "Accès aux cours premium",
    },
    {
        "slug": "pro",
        "name": "Pro",
        "price": "79.900",
        "duration_days": 90,
        "benefits": "Accès premium et accompagnement renforcé",
    },
]


def seed_demo(accounts):
    created_count = 0
    for plan_data in DEMO_PLANS:
        _, created = Plan.objects.update_or_create(
            slug=plan_data["slug"], defaults=plan_data
        )
        created_count += created
    return f"{len(DEMO_PLANS)} offres ({created_count} créées)"
