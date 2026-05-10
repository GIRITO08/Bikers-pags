from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class UserType(models.TextChoices):
        ADMIN = "admin", "Administrador"
        MOTOCICLISTA = "motociclista", "Motociclista"

    user_type = models.CharField(
        max_length=32,
        choices=UserType.choices,
        default=UserType.MOTOCICLISTA,
    )

    @property
    def photo_url(self) -> str:
        profile = getattr(self, "profile", None)
        if not profile:
            return ""
        if getattr(settings, "USE_LOCAL_MEDIA", False) and getattr(profile, "profile_photo_file", None):
            try:
                return profile.profile_photo_file.url
            except Exception:
                return ""
        return profile.profile_photo_url or ""

    @property
    def cover_url(self) -> str:
        profile = getattr(self, "profile", None)
        if not profile:
            return ""
        if getattr(settings, "USE_LOCAL_MEDIA", False) and getattr(profile, "cover_photo_file", None):
            try:
                return profile.cover_photo_file.url
            except Exception:
                return ""
        return profile.cover_photo_url or ""


class RiderProfile(models.Model):
    class Sex(models.TextChoices):
        FEMENINO = "F", "Femenino"
        MASCULINO = "M", "Masculino"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    document_id = models.CharField(max_length=64, blank=True)
    sex = models.CharField(max_length=1, choices=Sex.choices, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)

    residence_address_line1 = models.CharField(max_length=255, blank=True)
    residence_address_line2 = models.CharField(max_length=255, blank=True)
    residence_city = models.CharField(max_length=128, blank=True)
    residence_state = models.CharField(max_length=128, blank=True)
    residence_postal = models.CharField(max_length=32, blank=True)
    residence_country = models.CharField(max_length=128, blank=True)

    birth_place_line1 = models.CharField(max_length=255, blank=True)
    birth_place_line2 = models.CharField(max_length=255, blank=True)
    birth_place_city = models.CharField(max_length=128, blank=True)
    birth_place_state = models.CharField(max_length=128, blank=True)
    birth_place_country = models.CharField(max_length=128, blank=True)

    phone_home = models.CharField(max_length=64, blank=True)
    phone_mobile = models.CharField(max_length=64, blank=True)
    phone_work = models.CharField(max_length=64, blank=True)

    occupation = models.CharField(max_length=128, blank=True)
    contact_email = models.EmailField(blank=True)

    blood_type = models.CharField(max_length=8, blank=True)
    allergic = models.BooleanField(null=True, blank=True)
    allergy_details = models.CharField(max_length=255, blank=True)
    physical_condition = models.BooleanField(null=True, blank=True)
    physical_condition_details = models.CharField(max_length=255, blank=True)
    medical_treatment = models.BooleanField(null=True, blank=True)
    medical_treatment_details = models.CharField(max_length=255, blank=True)
    medication = models.BooleanField(null=True, blank=True)
    medication_supply = models.CharField(max_length=255, blank=True)
    has_medical_insurance = models.BooleanField(null=True, blank=True)
    medical_insurance_details = models.CharField(max_length=255, blank=True)

    vehicle_model = models.CharField(max_length=128, blank=True)
    vehicle_plate = models.CharField(max_length=32, blank=True)
    moto_model = models.CharField(max_length=128, blank=True)
    moto_plate = models.CharField(max_length=32, blank=True)

    profile_photo_url = models.URLField(blank=True, max_length=500)
    profile_photo_file = models.FileField(upload_to="profiles/avatars/", blank=True)
    cover_photo_url = models.URLField(blank=True, max_length=500)
    cover_photo_file = models.FileField(upload_to="profiles/covers/", blank=True)
    bio = models.TextField(blank=True)

    accepts_data_treatment = models.BooleanField(default=False)
    allows_photos = models.BooleanField(default=False)
    accepts_liability_release = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username}"


class EmergencyContact(models.Model):
    class ContactType(models.TextChoices):
        PRIMARY = "primary", "Principal"
        SECONDARY = "secondary", "Alternativo"

    profile = models.ForeignKey(RiderProfile, on_delete=models.CASCADE, related_name="emergency_contacts")
    contact_type = models.CharField(max_length=16, choices=ContactType.choices)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    relationship = models.CharField(max_length=128, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=128, blank=True)
    postal = models.CharField(max_length=32, blank=True)
    phone = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "contact_type"], name="uniq_emergency_contact_per_type")
        ]

    def __str__(self) -> str:
        return f"{self.get_contact_type_display()}: {self.first_name} {self.last_name}".strip()


class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        DECLINED = "declined", "Rechazada"

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    addressee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requester", "addressee"], name="uniq_friendship_request"),
            models.CheckConstraint(condition=~Q(requester=models.F("addressee")), name="no_self_friendship"),
        ]


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Post({self.author_id})"


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()


class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_comments")
    text = models.CharField(max_length=800)
    created_at = models.DateTimeField(auto_now_add=True)


class Trip(models.Model):
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TripImage(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()
