from django.db import migrations
from django.utils.text import slugify


DEFAULT_CATEGORIES = [
    "Développement web",
    "Data & IA",
    "DevOps",
    "Cybersécurité",
    "Réseaux",
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("courses", "Category")

    def unique_slug(name):
        base = slugify(name)[:84].strip("-") or "categorie"
        slug = base
        number = 2
        while Category.objects.filter(slug=slug).exists():
            slug = f"{base}-{number}"
            number += 1
        return slug

    for name in DEFAULT_CATEGORIES:
        category, created = Category.objects.get_or_create(
            name=name,
            defaults={"slug": unique_slug(name)},
        )
        if not created and not category.slug:
            category.slug = unique_slug(name)
            category.save(update_fields=["slug"])


def noop_reverse(apps, schema_editor):
    # Keep categories to avoid removing user-visible choices on rollback.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0003_alter_course_image_alter_resource_file"),
    ]

    operations = [
        migrations.RunPython(seed_categories, noop_reverse),
    ]
