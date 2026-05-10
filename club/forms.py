from __future__ import annotations

import os
import uuid
import urllib.error
import urllib.request

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.files.storage import default_storage

from .models import EmergencyContact, Post, PostComment, PostImage, RiderProfile, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario o Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Correo electrónico")

    document_id = forms.CharField(required=False, label="Documento de Identidad")
    sex = forms.ChoiceField(required=False, choices=RiderProfile.Sex.choices, label="Sexo")
    age = forms.IntegerField(required=False, min_value=0, label="Edad")
    birthdate = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Fecha de nacimiento")

    residence_address_line1 = forms.CharField(required=False, label="Dirección de residencia")
    residence_address_line2 = forms.CharField(required=False, label="Barrio")
    residence_city = forms.CharField(required=False, label="Ciudad")
    residence_state = forms.CharField(required=False, label="País/Estado")
    residence_postal = forms.CharField(required=False, label="Código Postal")
    residence_country = forms.CharField(required=False, label="País")

    birth_place_city = forms.CharField(required=False, label="Lugar de nacimiento (Ciudad)")
    birth_place_country = forms.CharField(required=False, label="Lugar de nacimiento (País)")

    phone_home = forms.CharField(required=False, label="Teléfono habitación")
    phone_mobile = forms.CharField(required=False, label="Teléfono móvil")
    phone_work = forms.CharField(required=False, label="Teléfono trabajo")

    occupation = forms.CharField(required=False, label="Ocupación")
    contact_email = forms.EmailField(required=False, label="Correo de contacto (alterno)")

    blood_type = forms.ChoiceField(
        required=False,
        choices=[("", "Seleccione")] + [(x, x) for x in ["A", "B", "AB", "O", "RH+", "RH-"]],
        label="Grupo sanguíneo",
    )
    allergic = forms.ChoiceField(required=False, choices=[("", "Seleccione"), ("1", "Sí"), ("0", "No")], label="¿Es alérgico?")
    allergy_details = forms.CharField(required=False, label="Alergias (especifique)")
    physical_condition = forms.ChoiceField(required=False, choices=[("", "Seleccione"), ("1", "Sí"), ("0", "No")], label="¿Padecimiento físico?")
    physical_condition_details = forms.CharField(required=False, label="Padecimiento (especifique)")
    medical_treatment = forms.ChoiceField(required=False, choices=[("", "Seleccione"), ("1", "Sí"), ("0", "No")], label="¿Tratamiento médico?")
    medical_treatment_details = forms.CharField(required=False, label="Tratamiento (especifique)")
    medication = forms.ChoiceField(required=False, choices=[("", "Seleccione"), ("1", "Sí"), ("0", "No")], label="¿Toma medicamentos?")
    medication_supply = forms.CharField(required=False, label="Forma de suministro (especifique)")
    has_medical_insurance = forms.ChoiceField(required=False, choices=[("", "Seleccione"), ("1", "Sí"), ("0", "No")], label="¿Posee seguro médico?")
    medical_insurance_details = forms.CharField(required=False, label="Seguro médico (especifique)")

    vehicle_model = forms.CharField(required=False, label="Vehículo modelo")
    vehicle_plate = forms.CharField(required=False, label="Vehículo placa")
    moto_model = forms.CharField(required=False, label="Moto modelo")
    moto_plate = forms.CharField(required=False, label="Moto placa")

    emergency_primary_first_name = forms.CharField(required=False, label="Emergencia (principal) - Nombres")
    emergency_primary_last_name = forms.CharField(required=False, label="Emergencia (principal) - Apellidos")
    emergency_primary_relationship = forms.CharField(required=False, label="Emergencia (principal) - Parentesco")
    emergency_primary_phone = forms.CharField(required=False, label="Emergencia (principal) - Teléfono")

    emergency_secondary_first_name = forms.CharField(required=False, label="Emergencia (alternativo) - Nombres")
    emergency_secondary_last_name = forms.CharField(required=False, label="Emergencia (alternativo) - Apellidos")
    emergency_secondary_phone = forms.CharField(required=False, label="Emergencia (alternativo) - Teléfono")

    profile_photo_url = forms.URLField(required=False, label="Foto (URL)")

    accepts_liability_release = forms.BooleanField(required=False, label="Acepto liberación de responsabilidad")
    accepts_data_treatment = forms.BooleanField(required=False, label="Acepto tratamiento de datos")
    allows_photos = forms.BooleanField(required=False, label="Autorizo fotografías")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error("email", "Este correo ya está registrado.")
        return cleaned

    @staticmethod
    def _to_bool(val: str | None) -> bool | None:
        if val in (None, ""):
            return None
        if val == "1":
            return True
        if val == "0":
            return False
        return None

    def save(self, commit: bool = True):
        user: User = super().save(commit=False)
        user.email = (self.cleaned_data.get("email") or "").strip().lower()
        user.user_type = User.UserType.MOTOCICLISTA
        if commit:
            user.save()

        profile, _ = RiderProfile.objects.get_or_create(user=user)
        profile.document_id = self.cleaned_data.get("document_id") or ""
        profile.sex = self.cleaned_data.get("sex") or ""
        profile.age = self.cleaned_data.get("age")
        profile.birthdate = self.cleaned_data.get("birthdate")

        profile.residence_address_line1 = self.cleaned_data.get("residence_address_line1") or ""
        profile.residence_address_line2 = self.cleaned_data.get("residence_address_line2") or ""
        profile.residence_city = self.cleaned_data.get("residence_city") or ""
        profile.residence_state = self.cleaned_data.get("residence_state") or ""
        profile.residence_postal = self.cleaned_data.get("residence_postal") or ""
        profile.residence_country = self.cleaned_data.get("residence_country") or ""

        profile.birth_place_city = self.cleaned_data.get("birth_place_city") or ""
        profile.birth_place_country = self.cleaned_data.get("birth_place_country") or ""

        profile.phone_home = self.cleaned_data.get("phone_home") or ""
        profile.phone_mobile = self.cleaned_data.get("phone_mobile") or ""
        profile.phone_work = self.cleaned_data.get("phone_work") or ""

        profile.occupation = self.cleaned_data.get("occupation") or ""
        profile.contact_email = (self.cleaned_data.get("contact_email") or "").strip().lower()

        profile.blood_type = self.cleaned_data.get("blood_type") or ""
        profile.allergic = self._to_bool(self.cleaned_data.get("allergic"))
        profile.allergy_details = self.cleaned_data.get("allergy_details") or ""
        profile.physical_condition = self._to_bool(self.cleaned_data.get("physical_condition"))
        profile.physical_condition_details = self.cleaned_data.get("physical_condition_details") or ""
        profile.medical_treatment = self._to_bool(self.cleaned_data.get("medical_treatment"))
        profile.medical_treatment_details = self.cleaned_data.get("medical_treatment_details") or ""
        profile.medication = self._to_bool(self.cleaned_data.get("medication"))
        profile.medication_supply = self.cleaned_data.get("medication_supply") or ""
        profile.has_medical_insurance = self._to_bool(self.cleaned_data.get("has_medical_insurance"))
        profile.medical_insurance_details = self.cleaned_data.get("medical_insurance_details") or ""

        profile.vehicle_model = self.cleaned_data.get("vehicle_model") or ""
        profile.vehicle_plate = self.cleaned_data.get("vehicle_plate") or ""
        profile.moto_model = self.cleaned_data.get("moto_model") or ""
        profile.moto_plate = self.cleaned_data.get("moto_plate") or ""

        profile.profile_photo_url = self.cleaned_data.get("profile_photo_url") or ""
        profile.accepts_liability_release = bool(self.cleaned_data.get("accepts_liability_release"))
        profile.accepts_data_treatment = bool(self.cleaned_data.get("accepts_data_treatment"))
        profile.allows_photos = bool(self.cleaned_data.get("allows_photos"))
        if commit:
            profile.save()

        if commit:
            self._upsert_emergency_contact(
                profile=profile,
                contact_type=EmergencyContact.ContactType.PRIMARY,
                first_name=self.cleaned_data.get("emergency_primary_first_name") or "",
                last_name=self.cleaned_data.get("emergency_primary_last_name") or "",
                relationship=self.cleaned_data.get("emergency_primary_relationship") or "",
                phone=self.cleaned_data.get("emergency_primary_phone") or "",
            )
            self._upsert_emergency_contact(
                profile=profile,
                contact_type=EmergencyContact.ContactType.SECONDARY,
                first_name=self.cleaned_data.get("emergency_secondary_first_name") or "",
                last_name=self.cleaned_data.get("emergency_secondary_last_name") or "",
                relationship="",
                phone=self.cleaned_data.get("emergency_secondary_phone") or "",
            )

        return user

    @staticmethod
    def _upsert_emergency_contact(
        *,
        profile: RiderProfile,
        contact_type: str,
        first_name: str,
        last_name: str,
        relationship: str,
        phone: str,
    ) -> None:
        if not (first_name.strip() or last_name.strip() or phone.strip()):
            return
        EmergencyContact.objects.update_or_create(
            profile=profile,
            contact_type=contact_type,
            defaults={
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "relationship": relationship.strip(),
                "phone": phone.strip(),
            },
        )


class ProfileEditForm(forms.Form):
    first_name = forms.CharField(required=False, label="Nombre(s)")
    last_name = forms.CharField(required=False, label="Apellidos")
    email = forms.EmailField(required=False, label="Correo")

    document_id = forms.CharField(required=False, label="Documento")
    sex = forms.ChoiceField(required=False, choices=[("", "-")] + list(RiderProfile.Sex.choices), label="Sexo")
    age = forms.IntegerField(required=False, min_value=0, label="Edad")
    birthdate = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Fecha de nacimiento")

    phone_mobile = forms.CharField(required=False, label="Teléfono móvil")
    phone_work = forms.CharField(required=False, label="Teléfono trabajo")
    residence_address_line1 = forms.CharField(required=False, label="Dirección")
    residence_address_line2 = forms.CharField(required=False, label="Barrio")
    residence_postal = forms.CharField(required=False, label="Código Postal")
    residence_country = forms.CharField(required=False, label="País")

    profile_photo_url = forms.URLField(required=False, label="Foto de perfil (URL)")
    profile_photo_file = forms.FileField(
        required=False,
        label="Foto de perfil",
        widget=forms.FileInput(attrs={"accept": "image/*"}),
    )
    cover_photo_url = forms.URLField(required=False, label="Foto de portada (URL)")
    cover_photo_file = forms.FileField(
        required=False,
        label="Foto de portada",
        widget=forms.FileInput(attrs={"accept": "image/*"}),
    )
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}), label="Bio")

    residence_city = forms.CharField(required=False, label="Ciudad")
    residence_state = forms.CharField(required=False, label="Estado")
    occupation = forms.CharField(required=False, label="Ocupación")

    blood_type = forms.ChoiceField(
        required=False,
        choices=[("", "-")] + [(x, x) for x in ["A", "B", "AB", "O", "RH+", "RH-"]],
        label="Grupo sanguíneo",
    )
    allergic = forms.ChoiceField(required=False, choices=[("", "-"), ("1", "Sí"), ("0", "No")], label="¿Es alérgico?")
    allergy_details = forms.CharField(required=False, label="Alergias (detalle)")
    moto_model = forms.CharField(required=False, label="Moto")
    moto_plate = forms.CharField(required=False, label="Placa")

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.profile, _ = RiderProfile.objects.get_or_create(user=user)
        if not self.is_bound:
            self.initial = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "document_id": self.profile.document_id,
                "sex": self.profile.sex,
                "age": self.profile.age,
                "birthdate": self.profile.birthdate,
                "phone_mobile": self.profile.phone_mobile,
                "phone_work": self.profile.phone_work,
                "residence_address_line1": self.profile.residence_address_line1,
                "residence_address_line2": self.profile.residence_address_line2,
                "profile_photo_url": self.profile.profile_photo_url,
                "cover_photo_url": getattr(self.profile, "cover_photo_url", ""),
                "bio": getattr(self.profile, "bio", ""),
                "residence_city": self.profile.residence_city,
                "residence_state": self.profile.residence_state,
                "residence_postal": self.profile.residence_postal,
                "residence_country": self.profile.residence_country,
                "occupation": self.profile.occupation,
                "blood_type": self.profile.blood_type,
                "allergic": "" if self.profile.allergic is None else ("1" if self.profile.allergic else "0"),
                "allergy_details": self.profile.allergy_details,
                "moto_model": self.profile.moto_model,
                "moto_plate": self.profile.moto_plate,
            }

    @staticmethod
    def _to_bool(val: str | None) -> bool | None:
        if val in (None, ""):
            return None
        if val == "1":
            return True
        if val == "0":
            return False
        return None

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(id=self.user.id).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def save(self):
        self.user.first_name = (self.cleaned_data.get("first_name") or "").strip()
        self.user.last_name = (self.cleaned_data.get("last_name") or "").strip()
        self.user.email = (self.cleaned_data.get("email") or "").strip().lower()
        self.user.save(update_fields=["first_name", "last_name", "email"])

        self.profile.document_id = (self.cleaned_data.get("document_id") or "").strip()
        self.profile.sex = (self.cleaned_data.get("sex") or "").strip()
        self.profile.age = self.cleaned_data.get("age")
        self.profile.birthdate = self.cleaned_data.get("birthdate")
        self.profile.phone_mobile = (self.cleaned_data.get("phone_mobile") or "").strip()
        self.profile.phone_work = (self.cleaned_data.get("phone_work") or "").strip()
        self.profile.residence_address_line1 = (self.cleaned_data.get("residence_address_line1") or "").strip()
        self.profile.residence_address_line2 = (self.cleaned_data.get("residence_address_line2") or "").strip()
        self.profile.residence_postal = (self.cleaned_data.get("residence_postal") or "").strip()
        self.profile.residence_country = (self.cleaned_data.get("residence_country") or "").strip()

        self.profile.profile_photo_url = (self.cleaned_data.get("profile_photo_url") or "").strip()
        self.profile.cover_photo_url = (self.cleaned_data.get("cover_photo_url") or "").strip()
        profile_file = self.cleaned_data.get("profile_photo_file")
        if profile_file:
            if getattr(settings, "USE_LOCAL_MEDIA", False):
                self.profile.profile_photo_file = profile_file
                self.profile.profile_photo_url = ""
            else:
                self.profile.profile_photo_url = self._upload_to_supabase_storage(profile_file, kind="avatar")
                self.profile.profile_photo_file = ""
        cover_file = self.cleaned_data.get("cover_photo_file")
        if cover_file:
            if getattr(settings, "USE_LOCAL_MEDIA", False):
                self.profile.cover_photo_file = cover_file
                self.profile.cover_photo_url = ""
            else:
                self.profile.cover_photo_url = self._upload_to_supabase_storage(cover_file, kind="cover")
                self.profile.cover_photo_file = ""
        self.profile.bio = (self.cleaned_data.get("bio") or "").strip()
        self.profile.residence_city = (self.cleaned_data.get("residence_city") or "").strip()
        self.profile.residence_state = (self.cleaned_data.get("residence_state") or "").strip()
        self.profile.occupation = (self.cleaned_data.get("occupation") or "").strip()
        self.profile.blood_type = (self.cleaned_data.get("blood_type") or "").strip()
        self.profile.allergic = self._to_bool(self.cleaned_data.get("allergic"))
        self.profile.allergy_details = (self.cleaned_data.get("allergy_details") or "").strip()
        self.profile.moto_model = (self.cleaned_data.get("moto_model") or "").strip()
        self.profile.moto_plate = (self.cleaned_data.get("moto_plate") or "").strip()
        self.profile.save(
            update_fields=[
                "document_id",
                "sex",
                "age",
                "birthdate",
                "phone_mobile",
                "phone_work",
                "residence_address_line1",
                "residence_address_line2",
                "residence_postal",
                "residence_country",
                "profile_photo_url",
                "profile_photo_file",
                "cover_photo_url",
                "cover_photo_file",
                "bio",
                "residence_city",
                "residence_state",
                "occupation",
                "blood_type",
                "allergic",
                "allergy_details",
                "moto_model",
                "moto_plate",
                "updated_at",
            ]
        )

    @staticmethod
    def _upload_to_supabase_storage(uploaded_file, *, kind: str) -> str:
        supabase_url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
        api_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
        bucket = (os.getenv("SUPABASE_STORAGE_BUCKET") or "profiles").strip()

        if not supabase_url:
            raise forms.ValidationError("Falta SUPABASE_URL en Vercel (Environment Variables).")
        if not api_key:
            raise forms.ValidationError("Falta SUPABASE_SERVICE_ROLE_KEY (o SUPABASE_ANON_KEY) en Vercel.")

        original_name = getattr(uploaded_file, "name", "") or "image"
        safe_name = "".join(c if c.isalnum() or c in {".", "_", "-"} else "_" for c in original_name)
        ext = ""
        if "." in safe_name:
            ext = "." + safe_name.rsplit(".", 1)[-1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"

        obj_name = f"{kind}/{uuid.uuid4().hex}{ext}"
        endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{obj_name}"
        content_type = getattr(uploaded_file, "content_type", None) or "application/octet-stream"

        try:
            data = uploaded_file.read()
        except Exception:
            data = b""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "apikey": api_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status not in (200, 201):
                    raise forms.ValidationError("No se pudo subir la imagen a Storage.")
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                body = ""
            raise forms.ValidationError(f"No se pudo subir la imagen a Storage ({e.code}). {body}".strip())
        except Exception:
            raise forms.ValidationError("No se pudo subir la imagen a Storage. Reintenta.")

        return f"{supabase_url}/storage/v1/object/public/{bucket}/{obj_name}"


class PostCreateForm(forms.Form):
    text = forms.CharField(
        required=False,
        label="",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Escribe algo..."}),
    )
    image_file = forms.FileField(
        required=False,
        label="",
        widget=forms.FileInput(attrs={"accept": "image/*"}),
    )

    def __init__(self, *args, user: User, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.request = request

    def clean(self):
        cleaned = super().clean()
        text = (cleaned.get("text") or "").strip()
        image_file = cleaned.get("image_file")
        if not text and not image_file:
            raise forms.ValidationError("Escribe algo o sube una foto.")
        return cleaned

    def save(self) -> Post:
        text = (self.cleaned_data.get("text") or "").strip()
        image_file = self.cleaned_data.get("image_file")

        post = Post.objects.create(author=self.user, text=text)

        if image_file:
            if getattr(settings, "USE_LOCAL_MEDIA", False):
                original_name = getattr(image_file, "name", "") or "image"
                safe_name = "".join(c if c.isalnum() or c in {".", "_", "-"} else "_" for c in original_name)
                ext = ""
                if "." in safe_name:
                    ext = "." + safe_name.rsplit(".", 1)[-1].lower()
                if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    ext = ".jpg"
                saved_name = default_storage.save(f"posts/{uuid.uuid4().hex}{ext}", image_file)
                url = self.request.build_absolute_uri(settings.MEDIA_URL + saved_name)
                PostImage.objects.create(post=post, url=url)
            else:
                url = ProfileEditForm._upload_to_supabase_storage(image_file, kind="posts")
                PostImage.objects.create(post=post, url=url)

        return post


class PostCommentForm(forms.Form):
    text = forms.CharField(
        required=True,
        label="",
        max_length=800,
        widget=forms.TextInput(attrs={"placeholder": "Escribe un comentario..."}),
    )

    def __init__(self, *args, user: User, post: Post, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.post = post

    def save(self) -> PostComment:
        text = (self.cleaned_data.get("text") or "").strip()
        return PostComment.objects.create(post=self.post, author=self.user, text=text)
