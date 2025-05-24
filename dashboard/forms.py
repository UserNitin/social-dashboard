from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, RedditPostSchedule

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'discord_bot_token', 'discord_channel_id',
            'reddit_client_id', 'reddit_client_secret',
            'reddit_user_agent', 'reddit_subreddit'
        ]

class RedditPostForm(forms.ModelForm):
    class Meta:
        model = RedditPostSchedule
        fields = ['title', 'content', 'url', 'scheduled_time']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }
