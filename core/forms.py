from django import forms
from django.db import models
from django.forms.boundfield import BoundField
from django.forms.renderers import TemplatesSetting


def bootstrap_class(widget):
    if widget.is_hidden:
        return ""
    if isinstance(widget, forms.CheckboxInput | forms.RadioSelect):
        return "form-check-input"
    if isinstance(widget, forms.Select):
        return "form-select"
    return "form-control"


class SkillForgeBoundField(BoundField):
    """Ajoute la classe Bootstrap du widget. Django pose déjà aria-invalid et aria-describedby."""

    def build_widget_attrs(self, attrs, widget=None):
        attrs = super().build_widget_attrs(attrs, widget)
        widget = widget or self.field.widget
        css_class = bootstrap_class(widget)
        if css_class:
            existing = attrs.get("class") or widget.attrs.get("class", "")
            attrs["class"] = f"{existing} {css_class}".strip()
        return attrs


class SkillForgeFormRenderer(TemplatesSetting):
    """Rendu commun à tous les formulaires du projet (réglage FORM_RENDERER)."""

    form_template_name = "core/forms/form.html"
    field_template_name = "core/forms/field.html"
    bound_field_class = SkillForgeBoundField


def https_url_formfield(model_field, **kwargs):
    """``formfield_callback`` des ModelForm : une URL saisie sans protocole devient https://.

    Django 6.0 passera à https par défaut ; le déclarer évite l'avertissement de dépréciation.
    """
    if isinstance(model_field, models.URLField):
        kwargs.setdefault("assume_scheme", "https")
    return model_field.formfield(**kwargs)
