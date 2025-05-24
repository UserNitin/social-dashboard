from django.shortcuts import render, redirect
import threading
import time
from datetime import datetime

import praw
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.timezone import make_aware, is_naive, timezone
from django.utils.dateparse import parse_datetime
from django.utils.timesince import timesince
from prawcore.exceptions import NotFound

from .forms import RegistrationForm, LoginForm, UserProfileForm, RedditPostForm
from .models import UserProfile, RedditPostSchedule, DiscordMessageSchedule

# ----- User Registration -----
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'dashboard/registration.html', {'form': form})

# ----- User Login -----
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request,
                                username=form.cleaned_data['username'],
                                password=form.cleaned_data['password'])
            if user:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid credentials.")
    else:
        form = LoginForm()
    return render(request, 'dashboard/login.html', {'form': form})

# ----- User Logout -----
@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# ----- Dashboard with Profile and API Setup -----
@login_required
def dashboard(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = None

    # Check if profile is complete
    profile_complete = profile is not None and all([
        profile.discord_bot_token, profile.discord_channel_id,
        profile.reddit_client_id, profile.reddit_client_secret,
        profile.reddit_user_agent, profile.reddit_subreddit
    ])

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()
            messages.success(request, "API settings saved successfully.")
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=profile)

    context = {
        'form': form,
        'profile_complete': profile_complete,
        'profile': profile
    }

    return render(request, 'dashboard/dashboard.html', context)

# ----- Discord API fetch messages -----
@login_required
def fetch_discord_messages(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        headers = {
            "Authorization": f"Bot {profile.discord_bot_token}"
        }
        response = requests.get(
            f"https://discord.com/api/v10/channels/{profile.discord_channel_id}/messages?limit=10",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            messages_list = [
                {
                    "content": msg["content"],
                    "author": msg["author"]["username"],
                    "avatar_url": f"https://cdn.discordapp.com/avatars/{msg['author']['id']}/{msg['author'].get('avatar', '')}.png" if msg['author'].get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png",
                    "timestamp": msg["timestamp"],
                    "timestamp_pretty": timesince(parse_datetime(msg["timestamp"])) + " ago" if msg.get("timestamp") else "",
                }
                for msg in reversed(data)  # oldest first
            ]
            return JsonResponse({"success": True, "messages": messages_list})
        else:
            return JsonResponse({"success": False, "error": "Failed to fetch messages."})
    except UserProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Profile not found."})

# ----- Discord API send message -----
@login_required
def send_discord_message(request):
    if request.method == "POST":
        try:
            profile = UserProfile.objects.get(user=request.user)
            # Accept both 'message' and 'content' keys
            message = request.POST.get('message')
            if message is None:
                message = request.POST.get('content')
            if message is not None:
                message = message.strip()
            if not message:
                return JsonResponse({"success": False, "error": "Empty message"})

            headers = {
                "Authorization": f"Bot {profile.discord_bot_token}",
                "Content-Type": "application/json"
            }
            payload = {"content": message}
            response = requests.post(
                f"https://discord.com/api/v10/channels/{profile.discord_channel_id}/messages",
                json=payload,
                headers=headers
            )
            if response.status_code in [200, 201, 204]:
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"success": False, "error": "Failed to send message."})
        except UserProfile.DoesNotExist:
            return JsonResponse({"success": False, "error": "Profile not found."})
    return JsonResponse({"success": False, "error": "Invalid request method"})

# ----- Reddit fetch posts -----
@login_required
def fetch_reddit_posts(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Reddit profile not found'})

    reddit = praw.Reddit(
        client_id=profile.reddit_client_id,
        client_secret=profile.reddit_client_secret,
        user_agent=profile.reddit_user_agent,
    )

    after = request.GET.get('after')
    subreddit = reddit.subreddit(profile.reddit_subreddit)
    posts = []
    limit = 10

    hot_posts = subreddit.hot(limit=100)  # Fetch more to allow skipping

    found_after = after is None
    count = 0
    last_post_name = None

    for post in hot_posts:
        if not found_after:
            if post.name == after:
                found_after = True
            continue
        if count >= limit:
            break
        media_type = "text"
        media_url = ""
        # --- Check for Reddit-hosted video
        if hasattr(post, 'media') and post.media and 'reddit_video' in post.media:
            media_type = "video"
            media_url = post.media['reddit_video']['fallback_url']
        # --- Check for image
        elif hasattr(post, 'preview') and 'images' in post.preview:
            media_type = "image"
            media_url = post.preview['images'][0]['source']['url'].replace("&amp;", "&")
        # --- Check if it's just a direct image link (like imgur or i.redd.it)
        elif post.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            media_type = "image"
            media_url = post.url

        posts.append({
            'id': post.id,
            'title': post.title,
            'author': str(post.author),
            'score': post.score,
            'url': post.url,
            'selftext': post.selftext,
            'media_type': media_type,
            'media_url': media_url,
            'permalink': post.permalink,
            'num_comments': post.num_comments
        })
        last_post_name = post.name  # fullname, e.g., t3_xxxxx
        count += 1

    # If less than limit posts, no more after
    next_after = last_post_name if count == limit else None

    return JsonResponse({'success': True, 'posts': posts, 'after': next_after})

# ----- Reddit post a new submission -----
@login_required
def comment_on_reddit_post(request):
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        comment_text = request.POST.get('comment')
        if not post_id or not comment_text:
            return JsonResponse({'success': False, 'error': 'Missing post ID or comment'})

        try:
            profile = UserProfile.objects.get(user=request.user)
            reddit = praw.Reddit(
                client_id=profile.reddit_client_id,
                client_secret=profile.reddit_client_secret,
                user_agent=profile.reddit_user_agent,
            )

            submission = reddit.submission(id=post_id)
            submission.reply(comment_text)

            return JsonResponse({'success': True, 'message': 'Comment posted successfully'})
        except NotFound:
            return JsonResponse({'success': False, 'error': 'Post not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def post_to_reddit(request):
    if request.method == "POST":
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Reddit profile not found'})

        title = request.POST.get('title')
        content = request.POST.get('content', '')
        url = request.POST.get('url', '')

        if not title:
            return JsonResponse({'success': False, 'error': 'Title is required'})

        reddit = praw.Reddit(
            client_id=profile.reddit_client_id,
            client_secret=profile.reddit_client_secret,
            user_agent=profile.reddit_user_agent,
        )

        subreddit = reddit.subreddit(profile.reddit_subreddit)
        try:
            if url:
                submission = subreddit.submit(title=title, url=url)
            else:
                submission = subreddit.submit(title=title, selftext=content)
            return JsonResponse({'success': True, 'post_id': submission.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# ----- Schedule a Reddit post -----
@login_required
def schedule_reddit_post(request):
    if request.method == "POST":
        form = RedditPostForm(request.POST, request.FILES)
        if form.is_valid():
            scheduled_post = form.save(commit=False)
            scheduled_post.user = request.user
            if is_naive(scheduled_post.scheduled_time):
                scheduled_post.scheduled_time = make_aware(scheduled_post.scheduled_time)
            # Save uploaded media if present
            if 'media' in request.FILES:
                scheduled_post.media = request.FILES['media']
            scheduled_post.save()
            messages.success(request, "Post scheduled successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid data in schedule post form.")
            return redirect('dashboard')
    else:
        return redirect('dashboard')

# ----- Background function to post scheduled Reddit posts -----
def reddit_scheduler():
    import django
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_dashboard.settings')
    django.setup()

    from django.utils import timezone
    from dashboard.models import RedditPostSchedule

    while True:
        now = timezone.now()
        pending_posts = RedditPostSchedule.objects.filter(posted=False, scheduled_time__lte=now)
        for post in pending_posts:
            try:
                profile = UserProfile.objects.get(user=post.user)
                reddit = praw.Reddit(
                    client_id=profile.reddit_client_id,
                    client_secret=profile.reddit_client_secret,
                    user_agent=profile.reddit_user_agent,
                )
                subreddit = reddit.subreddit(profile.reddit_subreddit)

                if post.url:
                    subreddit.submit(title=post.title, url=post.url)
                else:
                    subreddit.submit(title=post.title, selftext=post.content)

                post.posted = True
                post.save()
                print(f"Posted scheduled post {post.id} by {post.user.username}")
            except Exception as e:
                print(f"Error posting scheduled post {post.id}: {e}")

        time.sleep(60)  # Check every 1 minute

# Uncomment below to start scheduler thread automatically when app starts (optional)
scheduler_thread = threading.Thread(target=reddit_scheduler, daemon=True)
scheduler_thread.start()

@login_required
def schedule_discord_message(request):
    if request.method == "POST":
        message = request.POST.get('message', '').strip()
        scheduled_time = request.POST.get('scheduled_time')
        if not message or not scheduled_time:
            return JsonResponse({'success': False, 'error': 'Message and time required'})
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_time)
            if is_naive(scheduled_dt):
                scheduled_dt = make_aware(scheduled_dt)
            DiscordMessageSchedule.objects.create(
                user=request.user,
                message=message,
                scheduled_time=scheduled_dt
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def discord_scheduler():
    import django
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_dashboard.settings')
    django.setup()

    from dashboard.models import DiscordMessageSchedule, UserProfile

    while True:
        now = timezone.now()
        pending = DiscordMessageSchedule.objects.filter(sent=False, scheduled_time__lte=now)
        for msg in pending:
            try:
                profile = UserProfile.objects.get(user=msg.user)
                headers = {
                    "Authorization": f"Bot {profile.discord_bot_token}",
                    "Content-Type": "application/json"
                }
                payload = {"content": msg.message}
                response = requests.post(
                    f"https://discord.com/api/v10/channels/{profile.discord_channel_id}/messages",
                    json=payload,
                    headers=headers
                )
                if response.status_code in [200, 201, 204]:
                    msg.sent = True
                    msg.save()
            except Exception as e:
                print(f"Error sending scheduled Discord message {msg.id}: {e}")
        time.sleep(30)  # Check every 30 seconds

# Uncomment below to start scheduler thread automatically when app starts (optional)
scheduler_thread = threading.Thread(target=discord_scheduler, daemon=True)
scheduler_thread.start()
