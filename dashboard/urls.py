from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('api/discord/messages/', views.fetch_discord_messages, name='fetch_discord_messages'),
    path('api/discord/send_message/', views.send_discord_message, name='send_discord_message'),
    path('schedule_discord_message/', views.schedule_discord_message, name='schedule_discord_message'),

    path('api/reddit/posts/', views.fetch_reddit_posts, name='fetch_reddit_posts'),
    path('api/reddit/post/', views.post_to_reddit, name='post_to_reddit'),
    path('api/reddit/schedule_post/', views.schedule_reddit_post, name='schedule_reddit_post'),
]
