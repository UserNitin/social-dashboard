from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Discord API fields
    discord_bot_token = models.CharField(max_length=200, blank=True)
    discord_channel_id = models.CharField(max_length=100, blank=True)

    # Reddit API fields
    reddit_client_id = models.CharField(max_length=100, blank=True)
    reddit_client_secret = models.CharField(max_length=100, blank=True)
    reddit_user_agent = models.CharField(max_length=200, blank=True)
    reddit_subreddit = models.CharField(max_length=100, default='all', blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"

class RedditPostSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)
    url = models.URLField(blank=True)
    scheduled_time = models.DateTimeField()
    posted = models.BooleanField(default=False)

    def __str__(self):
        return f"Scheduled Post by {self.user.username} at {self.scheduled_time}"

class DiscordMessageSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    scheduled_time = models.DateTimeField()
    sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.user.username} at {self.scheduled_time}"
