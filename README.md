# Twitter Liked Tweets Digest Notifier

Automatically sends daily, weekly, and monthly email digests of your liked tweets using the Twitter API v2.

## Features

- **Daily Digest**: Sends email at 9 PM EST with tweets liked in the past 24 hours
- **Weekly Digest**: Sends email every Sunday at 9 PM with the week's liked tweets  
- **Monthly Digest**: Sends email on the last day of the month at 9 PM with the month's liked tweets
- **Rich HTML Email Format**: Includes tweet text, author info, direct links, and media previews
- **Pagination Support**: Fetches all liked tweets regardless of quantity
- **Duplicate Filtering**: Ensures no duplicate tweets across reports
- **Timezone Support**: Configurable timezone (default: America/New_York)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Twitter API Setup

1. Apply for Twitter API access at [developer.twitter.com](https://developer.twitter.com)
2. Create a new app and generate a Bearer Token
3. Get your Twitter User ID (you can use [tweeterid.com](https://tweeterid.com) to find it)

### 3. Email Configuration

For Gmail:
1. Enable 2-factor authentication
2. Generate an App Password (not your regular password)
3. Use `smtp.gmail.com` as SMTP host with port 587

For other providers:
- **Zoho**: `smtp.zoho.com`, port 587
- **Outlook**: `smtp-mail.outlook.com`, port 587
- **Yahoo**: `smtp.mail.yahoo.com`, port 587

### 4. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```ini
   TWITTER_BEARER_TOKEN=your_bearer_token_here
   TWITTER_USER_ID=your_twitter_user_id_here
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASS=your_app_password_here
   EMAIL_FROM=your_email@gmail.com
   EMAIL_TO=recipient@example.com
   TIMEZONE=America/New_York
   ```

## Usage

Run the script manually:

```bash
# Daily digest
python tweet_digest.py daily

# Weekly digest  
python tweet_digest.py weekly

# Monthly digest
python tweet_digest.py monthly
```

## Scheduling

### Option 1: Cron Jobs (Linux/macOS)

Edit your crontab:
```bash
crontab -e
```

Add these lines (adjust paths as needed):
```bash
# Daily digest at 9 PM EST
0 21 * * * cd /path/to/tweet-digest-notifier && python tweet_digest.py daily

# Weekly digest every Sunday at 9 PM EST  
0 21 * * 0 cd /path/to/tweet-digest-notifier && python tweet_digest.py weekly

# Monthly digest on the last day of the month at 9 PM EST
0 21 28-31 * * [ $(date -d tomorrow +\%d) -eq 1 ] && cd /path/to/tweet-digest-notifier && python tweet_digest.py monthly
```

### Option 2: GitHub Actions

Create `.github/workflows/tweet-digest.yml`:

```yaml
name: Tweet Digest Notifier

on:
  schedule:
    # Daily at 9 PM EST (1 AM UTC)
    - cron: '0 1 * * *'
    # Weekly on Sunday at 9 PM EST (1 AM UTC Monday)  
    - cron: '0 1 * * 1'
    # Monthly on the last day at 9 PM EST
    - cron: '0 1 28-31 * *'

jobs:
  send-digest:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run digest
      env:
        TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
        TWITTER_USER_ID: ${{ secrets.TWITTER_USER_ID }}
        SMTP_HOST: ${{ secrets.SMTP_HOST }}
        SMTP_PORT: ${{ secrets.SMTP_PORT }}
        SMTP_USER: ${{ secrets.SMTP_USER }}
        SMTP_PASS: ${{ secrets.SMTP_PASS }}
        EMAIL_FROM: ${{ secrets.EMAIL_FROM }}
        EMAIL_TO: ${{ secrets.EMAIL_TO }}
        TIMEZONE: ${{ secrets.TIMEZONE }}
      run: |
        if [ "${{ github.event.schedule }}" = "0 1 * * *" ]; then
          python tweet_digest.py daily
        elif [ "${{ github.event.schedule }}" = "0 1 * * 1" ]; then
          python tweet_digest.py weekly  
        else
          # Check if it's the last day of the month
          if [ $(date -d tomorrow +%d) -eq 1 ]; then
            python tweet_digest.py monthly
          fi
        fi
```

Add your credentials as GitHub repository secrets.

## Email Format

The emails are sent in HTML format with:
- Tweet text in styled blockquotes
- Clickable author usernames linking to their profiles
- Direct links to individual tweets
- Embedded media previews when available
- Responsive design for mobile devices

## Error Handling

The script includes comprehensive error handling for:
- Missing environment variables
- Twitter API rate limits and errors
- SMTP connection issues
- Network timeouts
- Invalid timeframe parameters

## Notes

- The Twitter API v2 doesn't provide the exact "liked_at" timestamp, so the script uses the tweet's creation time as a proxy
- Pagination ensures all liked tweets are retrieved regardless of quantity
- Duplicate tweets are automatically filtered out
- The script is timezone-aware and respects the configured timezone setting