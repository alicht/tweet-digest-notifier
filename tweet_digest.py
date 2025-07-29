#!/usr/bin/env python3
"""
Twitter Liked Tweets Digest Notifier
Sends daily, weekly, and monthly email digests of liked tweets.
"""

import os
import sys
import json
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple
import pytz
from dotenv import load_dotenv
import calendar

load_dotenv()

class TwitterDigest:
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.user_id = os.getenv('TWITTER_USER_ID')
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.email_from = os.getenv('EMAIL_FROM')
        self.email_to = os.getenv('EMAIL_TO')
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required environment variables are set."""
        required_vars = [
            'TWITTER_BEARER_TOKEN', 'TWITTER_USER_ID', 'SMTP_HOST', 
            'SMTP_USER', 'SMTP_PASS', 'EMAIL_FROM', 'EMAIL_TO'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for Twitter API requests."""
        return {"Authorization": f"Bearer {self.bearer_token}"}
    
    def fetch_liked_tweets(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        Fetch liked tweets within the specified time range.
        Uses pagination to get all tweets.
        """
        url = f"https://api.twitter.com/2/users/{self.user_id}/liked_tweets"
        
        params = {
            "tweet.fields": "created_at,author_id,public_metrics,attachments",
            "user.fields": "username,name",
            "expansions": "author_id,attachments.media_keys",
            "media.fields": "type,url,preview_image_url",
            "max_results": 100
        }
        
        all_tweets = []
        pagination_token = None
        
        while True:
            if pagination_token:
                params["pagination_token"] = pagination_token
            
            try:
                response = requests.get(url, headers=self.get_headers(), params=params)
                response.raise_for_status()
                data = response.json()
                
                if "data" not in data:
                    break
                
                tweets = data["data"]
                users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
                media = {m["media_key"]: m for m in data.get("includes", {}).get("media", [])}
                
                for tweet in tweets:
                    tweet_created = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                    
                    # Filter by time range (assuming liked_at is close to created_at for simplicity)
                    # Note: Twitter API v2 doesn't provide liked_at timestamp directly
                    if start_time <= tweet_created <= end_time:
                        author = users.get(tweet["author_id"], {})
                        tweet_media = []
                        
                        if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                            for media_key in tweet["attachments"]["media_keys"]:
                                if media_key in media:
                                    tweet_media.append(media[media_key])
                        
                        all_tweets.append({
                            "id": tweet["id"],
                            "text": tweet["text"],
                            "created_at": tweet_created,
                            "author": {
                                "username": author.get("username", "unknown"),
                                "name": author.get("name", "Unknown User")
                            },
                            "url": f"https://twitter.com/{author.get('username', 'unknown')}/status/{tweet['id']}",
                            "media": tweet_media
                        })
                
                pagination_token = data.get("meta", {}).get("next_token")
                if not pagination_token:
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"Error fetching tweets: {e}")
                break
        
        return all_tweets
    
    def filter_tweets_by_timeframe(self, tweets: List[Dict], timeframe: str) -> List[Dict]:
        """Filter tweets based on timeframe (daily, weekly, monthly)."""
        now = datetime.now(self.timezone)
        
        if timeframe == "daily":
            start_time = (now - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
            end_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
        elif timeframe == "weekly":
            days_since_sunday = now.weekday() + 1
            start_time = (now - timedelta(days=days_since_sunday + 6)).replace(hour=21, minute=0, second=0, microsecond=0)
            end_time = (now - timedelta(days=days_since_sunday - 1)).replace(hour=21, minute=0, second=0, microsecond=0)
        elif timeframe == "monthly":
            first_day = now.replace(day=1, hour=21, minute=0, second=0, microsecond=0)
            last_day = now.replace(day=calendar.monthrange(now.year, now.month)[1], hour=21, minute=0, second=0, microsecond=0)
            start_time = first_day
            end_time = last_day
        else:
            raise ValueError("Timeframe must be 'daily', 'weekly', or 'monthly'")
        
        return [tweet for tweet in tweets if start_time <= tweet["created_at"] <= end_time]
    
    def generate_html_email(self, tweets: List[Dict], timeframe: str) -> Tuple[str, str]:
        """Generate HTML email content and subject."""
        now = datetime.now(self.timezone)
        
        if timeframe == "daily":
            subject = f"Your Liked Tweets Digest  {now.strftime('%B %d, %Y')}"
            title = "Daily Liked Tweets Digest"
        elif timeframe == "weekly":
            week_start = now - timedelta(days=now.weekday() + 1)
            subject = f"Your Weekly Liked Tweets Summary  Week of {week_start.strftime('%B %d')}"
            title = "Weekly Liked Tweets Summary"
        else:  # monthly
            subject = f"Your Liked Tweets Recap  {now.strftime('%B %Y')}"
            title = "Monthly Liked Tweets Recap"
        
        if not tweets:
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #1da1f2;">{title}</h2>
                <p>No liked tweets found for this period.</p>
            </body>
            </html>
            """
            return subject, html_content
        
        tweet_html = ""
        for tweet in tweets:
            media_html = ""
            if tweet["media"]:
                for media_item in tweet["media"]:
                    if media_item.get("type") == "photo" and media_item.get("url"):
                        media_html += f'<img src="{media_item["url"]}" style="max-width: 100%; margin: 10px 0;" alt="Tweet media">'
                    elif media_item.get("preview_image_url"):
                        media_html += f'<img src="{media_item["preview_image_url"]}" style="max-width: 100%; margin: 10px 0;" alt="Media preview">'
            
            tweet_html += f"""
            <div style="border: 1px solid #e1e8ed; border-radius: 12px; padding: 16px; margin: 16px 0; background: #f7f9fa;">
                <blockquote style="margin: 0; font-style: italic; color: #14171a;">
                    "{tweet['text']}"
                </blockquote>
                <div style="margin-top: 12px;">
                    <strong>
                        <a href="https://twitter.com/{tweet['author']['username']}" 
                           style="color: #1da1f2; text-decoration: none;">
                            @{tweet['author']['username']}
                        </a>
                    </strong>
                    ({tweet['author']['name']})
                </div>
                {media_html}
                <div style="margin-top: 8px; font-size: 12px; color: #657786;">
                    <a href="{tweet['url']}" style="color: #1da1f2;">View Tweet</a> " 
                    Liked: {tweet['created_at'].strftime('%B %d, %Y at %I:%M %p')}
                </div>
            </div>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1da1f2; text-align: center;">{title}</h2>
            <p style="text-align: center; color: #657786;">
                Found {len(tweets)} liked tweet{"s" if len(tweets) != 1 else ""}
            </p>
            {tweet_html}
            <hr style="margin: 32px 0; border: none; border-top: 1px solid #e1e8ed;">
            <p style="text-align: center; font-size: 12px; color: #657786;">
                Generated by Tweet Digest Notifier
            </p>
        </body>
        </html>
        """
        
        return subject, html_content
    
    def send_email(self, subject: str, html_content: str):
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            print(f"Email sent successfully: {subject}")
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            raise
    
    def run_digest(self, timeframe: str):
        """Run the digest for the specified timeframe."""
        print(f"Running {timeframe} digest...")
        
        try:
            # Calculate time range for API call (get more data than needed, then filter)
            now = datetime.now(self.timezone)
            if timeframe == "daily":
                start_time = now - timedelta(days=2)
            elif timeframe == "weekly":
                start_time = now - timedelta(days=14)
            else:  # monthly
                start_time = now - timedelta(days=32)
            
            end_time = now
            
            # Fetch tweets
            all_tweets = self.fetch_liked_tweets(start_time, end_time)
            
            # Filter by exact timeframe
            filtered_tweets = self.filter_tweets_by_timeframe(all_tweets, timeframe)
            
            # Remove duplicates
            seen_ids = set()
            unique_tweets = []
            for tweet in filtered_tweets:
                if tweet["id"] not in seen_ids:
                    seen_ids.add(tweet["id"])
                    unique_tweets.append(tweet)
            
            # Generate and send email
            subject, html_content = self.generate_html_email(unique_tweets, timeframe)
            self.send_email(subject, html_content)
            
        except Exception as e:
            print(f"Error running {timeframe} digest: {e}")
            sys.exit(1)

def main():
    """Main function to run the script."""
    if len(sys.argv) != 2:
        print("Usage: python tweet_digest.py [daily|weekly|monthly]")
        sys.exit(1)
    
    timeframe = sys.argv[1].lower()
    if timeframe not in ['daily', 'weekly', 'monthly']:
        print("Timeframe must be 'daily', 'weekly', or 'monthly'")
        sys.exit(1)
    
    digest = TwitterDigest()
    digest.run_digest(timeframe)

if __name__ == "__main__":
    main()