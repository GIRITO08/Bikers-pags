from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django import forms

from .forms import LoginForm, PostCommentForm, PostCreateForm, ProfileEditForm, RegisterForm
from .models import Friendship, Post, PostComment, RiderProfile, Trip, User


def home(request: HttpRequest):
    return redirect("info")


def info_view(request: HttpRequest):
    return render(request, "club/info.html", {
        "club_name": "Tesalia Motoclub",
        "club_tagline": "Pasión sobre dos ruedas",
    })


def login_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("feed")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            raw_username = (form.cleaned_data.get("username") or "").strip()
            password = form.cleaned_data.get("password")

            username = raw_username
            if "@" in raw_username:
                user = User.objects.filter(email__iexact=raw_username).only("username").first()
                if user:
                    username = user.username

            user = authenticate(request, username=username, password=password)
            if user is None:
                messages.error(request, "Usuario/email o contraseña incorrectos.")
            else:
                login(request, user)
                return redirect("feed")
        else:
            messages.error(request, "No se pudo iniciar sesión. Revisa usuario/email y contraseña.")

    return render(request, "club/login.html", {"form": form})


def register_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("feed")

    form = RegisterForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("feed")
        messages.error(request, "No se pudo crear la cuenta. Revisa los campos marcados.")

    return render(request, "club/register.html", {"form": form})


def logout_view(request: HttpRequest):
    logout(request)
    return redirect("home")


def _friends_queryset(user: User):
    return Friendship.objects.filter(
        status=Friendship.Status.ACCEPTED,
    ).filter(Q(requester=user) | Q(addressee=user))

 
def _attach_friendship_meta(me: User, users: list[User]) -> None:
    ids = [u.id for u in users if u.id and u.id != me.id]
    if not ids:
        return
    rels = (
        Friendship.objects.filter(
            Q(requester=me, addressee_id__in=ids) | Q(addressee=me, requester_id__in=ids)
        )
        .select_related("requester", "addressee")
        .order_by("-created_at")
    )
    by_other: dict[int, Friendship] = {}
    for fr in rels:
        other_id = fr.addressee_id if fr.requester_id == me.id else fr.requester_id
        if other_id and other_id not in by_other:
            by_other[other_id] = fr
    for u in users:
        fr = by_other.get(u.id)
        u.friend_status = fr.status if fr else ""
        u.friend_request_id = fr.id if fr else 0
        if fr:
            u.friend_dir = "out" if fr.requester_id == me.id else "in"
        else:
            u.friend_dir = ""


@login_required
def feed(request: HttpRequest):
    posts = (
        Post.objects.select_related("author", "author__profile")
        .prefetch_related(
            "images",
            Prefetch(
                "comments",
                queryset=PostComment.objects.select_related("author", "author__profile").order_by("created_at"),
            ),
        )
        .order_by("-created_at")[:25]
    )
    trips = Trip.objects.prefetch_related("images").order_by("-created_at")[:10]

    accepted_friendships = _friends_queryset(request.user).select_related("requester", "addressee")
    friends = []
    for fr in accepted_friendships:
        friends.append(fr.addressee if fr.requester_id == request.user.id else fr.requester)

    friend_suggestions = list(
        User.objects.exclude(id=request.user.id)
        .exclude(id__in=[u.id for u in friends])
        .select_related("profile")
        .order_by("date_joined")[:8]
    )
    _attach_friendship_meta(request.user, friend_suggestions)

    incoming_requests = (
        Friendship.objects.filter(addressee=request.user, status=Friendship.Status.PENDING)
        .select_related("requester", "requester__profile")
        .order_by("-created_at")[:10]
    )

    fallback_posts = []
    if not posts:
        fallback_posts = [
            {
                "author_name": "Tesalia Motoclub",
                "author_photo": "https://images.unsplash.com/photo-1558981403-c5ak3d0f2394?auto=format&fit=crop&w=160&h=160&q=80",
                "created_at": date.today(),
                "text": "Bienvenido/a. Aquí puedes encontrar riders, agregar amigos y ver viajes del club.",
                "images": [
                    "https://images.unsplash.com/photo-1525104885119-8806dd1f5a8f?auto=format&fit=crop&w=1200&q=80",
                ],
            }
        ]

    fallback_trips = []
    if not trips:
        fallback_trips = [
            {
                "title": "Rodada de bienvenida",
                "images": [
                    "https://images.unsplash.com/photo-1526726538690-5cbf956ae2fd?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?auto=format&fit=crop&w=1200&q=80",
                ],
            }
        ]

    return render(
        request,
        "club/feed.html",
        {
            "posts": posts,
            "trips": trips,
            "friends": friends,
            "friend_suggestions": friend_suggestions,
            "incoming_requests": incoming_requests,
            "fallback_posts": fallback_posts,
            "fallback_trips": fallback_trips,
            "post_form": PostCreateForm(user=request.user, request=request),
        },
    )


@login_required
@require_POST
def post_create(request: HttpRequest):
    form = PostCreateForm(request.POST or None, request.FILES or None, user=request.user, request=request)
    if form.is_valid():
        try:
            form.save()
        except forms.ValidationError as e:
            msg = ""
            if hasattr(e, "messages") and e.messages:
                msg = e.messages[0]
            messages.error(request, msg or "No se pudo publicar. Reintenta.")
        except Exception:
            messages.error(request, "No se pudo publicar. Reintenta.")
        else:
            messages.success(request, "Publicación creada.")
    else:
        messages.error(request, "No se pudo publicar. Revisa el texto o la imagen.")
    return redirect("feed")


@login_required
@require_POST
def post_comment(request: HttpRequest, post_id: int):
    post = get_object_or_404(Post, id=post_id)
    form = PostCommentForm(request.POST or None, user=request.user, post=post)
    if form.is_valid():
        form.save()
    else:
        messages.error(request, "Comentario inválido.")
    return redirect("feed")


@login_required
def riders(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.select_related("profile").order_by("username")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    riders_list = list(qs[:200])
    _attach_friendship_meta(request.user, riders_list)
    return render(request, "club/riders.html", {"riders": riders_list, "q": q})


@login_required
def rider_detail(request: HttpRequest, username: str):
    rider = get_object_or_404(User, username=username)
    profile, _ = RiderProfile.objects.get_or_create(user=rider)
    can_view_private = settings.ALLOW_PUBLIC_PROFILE_VIEW or request.user.is_staff or request.user.is_superuser
    if rider.id != request.user.id:
        _attach_friendship_meta(request.user, [rider])
    return render(
        request,
        "club/rider_detail.html",
        {"rider": rider, "profile": profile, "can_view_private": can_view_private},
    )


@login_required
def me_edit(request: HttpRequest):
    profile, _ = RiderProfile.objects.get_or_create(user=request.user)
    form = ProfileEditForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
            except forms.ValidationError as e:
                msg = ""
                if hasattr(e, "messages") and e.messages:
                    msg = e.messages[0]
                messages.error(request, msg or "No se pudo subir la imagen. Revisa tu configuración de Supabase Storage o usa URL.")
                return render(request, "club/profile_edit.html", {"form": form, "profile": profile})
            except Exception:
                messages.error(request, "No se pudo subir la imagen. Revisa tu configuración de Supabase Storage o usa URL.")
                return render(request, "club/profile_edit.html", {"form": form, "profile": profile})
            else:
                messages.success(request, "Perfil actualizado.")
                return redirect("rider_detail", username=request.user.username)
        else:
            messages.error(request, "No se pudo guardar. Revisa los campos marcados.")
    return render(request, "club/profile_edit.html", {"form": form, "profile": profile})


@login_required
@require_GET
def api_search(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})
    qs = (
        User.objects.select_related("profile")
        .filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        .order_by("username")[:15]
    )
    results = []
    for u in qs:
        results.append(
            {
                "id": u.id,
                "username": u.username,
                "name": u.get_full_name() or u.username,
                "photo": getattr(u.profile, "profile_photo_url", "") if hasattr(u, "profile") else "",
            }
        )
    return JsonResponse({"results": results})


@login_required
@require_POST
def api_friend_request(request: HttpRequest):
    try:
        target_id = int(request.POST.get("user_id", "0"))
    except ValueError:
        target_id = 0
    if not target_id or target_id == request.user.id:
        return JsonResponse({"ok": False, "error": "Usuario inválido."}, status=400)

    target = get_object_or_404(User, id=target_id)

    existing = Friendship.objects.filter(
        Q(requester=request.user, addressee=target) | Q(requester=target, addressee=request.user)
    ).first()
    if existing:
        return JsonResponse({"ok": True, "status": existing.status})

    fr = Friendship.objects.create(requester=request.user, addressee=target, status=Friendship.Status.PENDING)
    return JsonResponse({"ok": True, "status": fr.status})


@login_required
@require_POST
def api_friend_accept(request: HttpRequest):
    try:
        request_id = int(request.POST.get("request_id", "0"))
    except ValueError:
        request_id = 0
    fr = get_object_or_404(Friendship, id=request_id, addressee=request.user)
    fr.status = Friendship.Status.ACCEPTED
    fr.save(update_fields=["status", "updated_at"])
    return JsonResponse(
        {
            "ok": True,
            "status": fr.status,
            "requester_id": fr.requester_id,
            "addressee_id": fr.addressee_id,
        }
    )


@login_required
@require_GET
def api_friend_updates(request: HttpRequest):
    raw_since = (request.GET.get("since") or "").strip()
    since_dt = None
    if raw_since.isdigit():
        since_ms = int(raw_since)
        since_dt = datetime.fromtimestamp(since_ms / 1000.0, tz=timezone.utc)
    if since_dt is None:
        since_dt = datetime.fromtimestamp(0, tz=timezone.utc)

    updates = (
        Friendship.objects.filter(
            requester=request.user,
            status=Friendship.Status.ACCEPTED,
            updated_at__gt=since_dt,
        )
        .select_related("addressee", "addressee__profile")
        .order_by("updated_at")[:20]
    )
    events = []
    for fr in updates:
        u = fr.addressee
        events.append(
            {
                "id": fr.id,
                "user_id": u.id,
                "username": u.username,
                "name": u.get_full_name() or u.username,
                "ts": int(fr.updated_at.timestamp() * 1000),
            }
        )
    return JsonResponse({"ok": True, "events": events, "now": int(timezone.now().timestamp() * 1000)})


@login_required
@require_GET
def api_friend_incoming(request: HttpRequest):
    raw_since = (request.GET.get("since") or "").strip()
    since_dt = None
    if raw_since.isdigit():
        since_ms = int(raw_since)
        since_dt = datetime.fromtimestamp(since_ms / 1000.0, tz=timezone.utc)
    if since_dt is None:
        since_dt = datetime.fromtimestamp(0, tz=timezone.utc)

    qs = Friendship.objects.filter(addressee=request.user, status=Friendship.Status.PENDING)
    total = qs.count()
    new_reqs = (
        qs.filter(created_at__gt=since_dt)
        .select_related("requester", "requester__profile")
        .order_by("created_at")[:20]
    )
    events = []
    for fr in new_reqs:
        u = fr.requester
        events.append(
            {
                "id": fr.id,
                "user_id": u.id,
                "username": u.username,
                "name": u.get_full_name() or u.username,
                "ts": int(fr.created_at.timestamp() * 1000),
            }
        )
    return JsonResponse({"ok": True, "count": total, "events": events, "now": int(timezone.now().timestamp() * 1000)})

@login_required
@require_GET
def api_notifications_check(request: HttpRequest):
    raw_since = (request.GET.get("since") or "").strip()
    since_dt = None
    if raw_since.isdigit():
        since_ms = int(raw_since)
        since_dt = datetime.fromtimestamp(since_ms / 1000.0, tz=timezone.utc)
    if since_dt is None:
        since_dt = datetime.fromtimestamp(0, tz=timezone.utc)

    # Check for new friend requests
    new_friend_requests = Friendship.objects.filter(
        addressee=request.user, 
        status=Friendship.Status.PENDING, 
        created_at__gt=since_dt
    ).exists()

    # Check for new comments on user's posts
    new_comments = PostComment.objects.filter(
        post__author=request.user, 
        created_at__gt=since_dt
    ).exclude(author=request.user).exists()

    # Check for new posts from other users
    new_posts = Post.objects.filter(
        created_at__gt=since_dt
    ).exclude(author=request.user).exists()

    has_new_events = new_friend_requests or new_comments or new_posts

    return JsonResponse({
        "ok": True, 
        "has_new_events": has_new_events, 
        "now": int(timezone.now().timestamp() * 1000)
    })

