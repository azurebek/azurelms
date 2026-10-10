"""Durable design state. All application mutations belong to design_service."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableDesignQuerySet(models.QuerySet):
    def update(self, **kwargs):
        # Account removal may clear attribution's FK, never the retained label
        # or snapshot. Django's SET_NULL collector uses this update path.
        if kwargs == {"actor": None}:
            return super().update(**kwargs)
        raise ValidationError("Dizayn tarixi o‘zgarmas. Yangi versiya yarating.")

    def delete(self):
        raise ValidationError("Dizayn tarixi o‘chirilmaydi.")


class ImmutableDesignRecord(models.Model):
    objects = ImmutableDesignQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Dizayn tarixi o‘zgarmas. Yangi versiya yarating.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Dizayn tarixi o‘chirilmaydi.")


class DesignVersion(ImmutableDesignRecord):
    number = models.PositiveBigIntegerField(unique=True)
    value = models.JSONField()
    kind = models.CharField(max_length=12, choices=(("factory", "Asl"), ("publish", "Nashr"), ("rollback", "Qaytish")))
    reason = models.CharField(max_length=240)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    actor_label = models.CharField(max_length=150, blank=True)
    source_version = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-number",)
        base_manager_name = "objects"


class DesignState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    current_version = models.ForeignKey(DesignVersion, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="core_design_singleton")]


class DesignDraft(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="design_draft")
    revision = models.PositiveBigIntegerField(default=1)
    base_version = models.PositiveBigIntegerField(default=0)
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DesignPreset(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="design_presets")
    name = models.CharField(max_length=60)
    name_key = models.CharField(max_length=180, editable=False)
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name", "pk")
        constraints = [models.UniqueConstraint(fields=("owner", "name_key"), condition=models.Q(deleted_at__isnull=True),
                                              name="core_design_preset_name")]


class DesignOperation(ImmutableDesignRecord):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    actor_label = models.CharField(max_length=150, blank=True)
    operation = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    command = models.CharField(max_length=20)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "objects"
        constraints = [models.UniqueConstraint(fields=("actor", "operation"), name="core_design_operation_owner")]
