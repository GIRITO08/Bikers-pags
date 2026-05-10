from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="home"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/register/", views.register_view, name="register"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("feed/", views.feed, name="feed"),
    path("posts/create/", views.post_create, name="post_create"),
    path("posts/<int:post_id>/comment/", views.post_comment, name="post_comment"),
    path("riders/", views.riders, name="riders"),
    path("riders/<str:username>/", views.rider_detail, name="rider_detail"),
    path("me/edit/", views.me_edit, name="me_edit"),
    path("api/search/", views.api_search, name="api_search"),
    path("api/friends/request/", views.api_friend_request, name="api_friend_request"),
    path("api/friends/accept/", views.api_friend_accept, name="api_friend_accept"),
    path("api/friends/updates/", views.api_friend_updates, name="api_friend_updates"),
    path("api/friends/incoming/", views.api_friend_incoming, name="api_friend_incoming"),
]
