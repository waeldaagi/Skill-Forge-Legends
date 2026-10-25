from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="nom")),
                ("slug", models.SlugField(max_length=140, unique=True, verbose_name="slug")),
                ("price", models.DecimalField(decimal_places=3, max_digits=8, validators=[django.core.validators.MinValueValidator(0)], verbose_name="prix (TND)")),
                ("duration_days", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="durée (jours)")),
                ("benefits", models.TextField(blank=True, verbose_name="avantages")),
                ("is_active", models.BooleanField(default=True, verbose_name="active")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["price", "name"]},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=3, max_digits=8, validators=[django.core.validators.MinValueValidator(0)], verbose_name="montant")),
                ("currency", models.CharField(default="TND", editable=False, max_length=3, verbose_name="devise")),
                ("status", models.CharField(choices=[("EN_ATTENTE", "En attente"), ("REUSSI", "Réussi"), ("ECHOUE", "Échoué")], default="EN_ATTENTE", max_length=12, verbose_name="statut")),
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="référence")),
                ("provider", models.CharField(default="simulation", editable=False, max_length=30, verbose_name="fournisseur")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="payments.plan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_at", models.DateTimeField(verbose_name="débute le")),
                ("ends_at", models.DateTimeField(verbose_name="se termine le")),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("EXPIREE", "Expirée"), ("ANNULEE", "Annulée")], default="ACTIVE", max_length=10, verbose_name="statut")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to="payments.plan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subscriptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.CharField(max_length=30, unique=True, verbose_name="numéro")),
                ("pdf", models.FileField(blank=True, upload_to="invoices/%Y/%m/", verbose_name="facture PDF")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("payment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="invoice", to="payments.payment")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="subscription", index=models.Index(fields=["user", "status", "ends_at"], name="payments_s_user_id_7d7f1f_idx")),
    ]
