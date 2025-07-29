#!/usr/bin/env python3
"""
Twitter Liked Tweets Scraper using Playwright with Cookie Authentication
Scrapes liked tweets from Twitter/X using saved session cookies.
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import pytz

load_dotenv()

class TwitterScraper:
    def __init__(self):
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
        self.cookies_file = 'twitter_cookies.json'
    
    async def load_cookies(self, context) -> bool:
        """Load Twitter cookies from file."""
        try:
            if not os.path.exists(self.cookies_file):
                print(f"Cookie file {self.cookies_file} not found.")
                print("Please run save_cookies.py first to generate session cookies.")
                return False
            
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            
            if not cookies:
                print("Cookie file is empty.")
                return False
            
            await context.add_cookies(cookies)
            print(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
            return True
            
        except json.JSONDecodeError:
            print(f"Cookie file {self.cookies_file} is malformed. Please regenerate it.")
            return False
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return False
    
    async def check_login_status(self, page: Page) -> bool:
        """Check if we're logged in by looking for login indicators."""
        try:
            # Check if we're redirected to login page
            current_url = page.url
            if 'login' in current_url or 'flow/login' in current_url:
                return False
            
            # Look for logged-in indicators
            login_indicators = [
                '[data-testid="AppTabBar_Home_Link"]',
                '[data-testid="SideNav_AccountSwitcher_Button"]',
                '[data-testid="primaryColumn"]',
                '[aria-label="Home timeline"]'
            ]
            
            for indicator in login_indicators:
                element = await page.query_selector(indicator)
                if element:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking login status: {e}")
            return False
    
    async def navigate_to_likes(self, page: Page) -> bool:
        """Navigate to the likes page."""
        try:
            print("Navigating to likes page...")
            await page.goto('https://twitter.com/i/likes', wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Check if we're still logged in
            if not await self.check_login_status(page):
                print("Session expired. Please refresh your twitter_cookies.json file.")
                print("Run save_cookies.py to get new session cookies.")
                return False
            
            # Wait for tweets to load
            try:
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                print("Likes page loaded successfully!")
                return True
            except:
                print("No tweets found on likes page. This might be normal if you have no likes.")
                return True
                
        except Exception as e:
            print(f"Error navigating to likes: {e}")
            return False
    
    async def scroll_and_load_tweets(self, page: Page, num_scrolls: int = 5) -> None:
        """Scroll the page to load more tweets."""
        print(f"Scrolling to load more tweets ({num_scrolls} scrolls)...")
        
        for i in range(num_scrolls):
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait a bit for new content to load
            await asyncio.sleep(2)
            
            print(f"Completed scroll {i + 1}/{num_scrolls}")
    
    def parse_timestamp(self, time_text: str) -> Optional[datetime]:
        """Parse relative timestamp like '2h', '1d', '3m' to datetime."""
        if not time_text:
            return None
            
        now = datetime.now(self.timezone)
        time_text = time_text.lower().strip()
        
        # Handle different time formats
        if 'm' in time_text and time_text.replace('m', '').isdigit():
            # Minutes ago
            minutes = int(time_text.replace('m', ''))
            return now - timedelta(minutes=minutes)
        elif 'h' in time_text and time_text.replace('h', '').isdigit():
            # Hours ago
            hours = int(time_text.replace('h', ''))
            return now - timedelta(hours=hours)
        elif 'd' in time_text and time_text.replace('d', '').isdigit():
            # Days ago
            days = int(time_text.replace('d', ''))
            return now - timedelta(days=days)
        
        # If we can't parse it, assume it's older than 24 hours
        return now - timedelta(days=2)
    
    async def extract_tweet_data(self, page: Page) -> List[Dict]:
        """Extract tweet data from the current page."""
        print("Extracting tweet data...")
        
        # Get all tweet articles
        tweet_elements = await page.query_selector_all('article[data-testid="tweet"]')
        tweets = []
        
        for element in tweet_elements:
            try:
                tweet_data = {}
                
                # Extract tweet text
                text_element = await element.query_selector('[data-testid="tweetText"]')
                if text_element:
                    tweet_data['text'] = await text_element.inner_text()
                else:
                    continue  # Skip if no text found
                
                # Skip promoted tweets and retweets
                if not tweet_data['text'] or 'Promoted' in tweet_data['text']:
                    continue
                
                # Check for retweet indicators
                retweet_element = await element.query_selector('[data-testid="socialContext"]')
                if retweet_element:
                    retweet_text = await retweet_element.inner_text()
                    if 'retweeted' in retweet_text.lower():
                        continue  # Skip retweets
                
                # Extract author handle
                author_element = await element.query_selector('[data-testid="User-Name"] span:has-text("@")')
                if author_element:
                    author_text = await author_element.inner_text()
                    tweet_data['author_handle'] = author_text.strip()
                else:
                    tweet_data['author_handle'] = '@unknown'
                
                # Extract tweet link
                link_element = await element.query_selector('a[href*="/status/"]')
                if link_element:
                    href = await link_element.get_attribute('href')
                    if href.startswith('/'):
                        tweet_data['url'] = f"https://twitter.com{href}"
                    else:
                        tweet_data['url'] = href
                else:
                    tweet_data['url'] = ''
                
                # Extract timestamp
                time_element = await element.query_selector('time')
                if time_element:
                    datetime_attr = await time_element.get_attribute('datetime')
                    if datetime_attr:
                        # Parse ISO timestamp
                        tweet_data['timestamp'] = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                    else:
                        # Fallback to relative time text
                        time_text = await time_element.inner_text()
                        tweet_data['timestamp'] = self.parse_timestamp(time_text)
                else:
                    tweet_data['timestamp'] = None
                
                # Extract media (images/videos)
                media_urls = []
                
                # Look for images
                img_elements = await element.query_selector_all('img[src*="media"]')
                for img in img_elements:
                    src = await img.get_attribute('src')
                    if src and 'media' in src:
                        media_urls.append({
                            'type': 'image',
                            'url': src
                        })
                
                # Look for videos
                video_elements = await element.query_selector_all('video')
                for video in video_elements:
                    poster = await video.get_attribute('poster')
                    if poster:
                        media_urls.append({
                            'type': 'video',
                            'preview_url': poster
                        })
                
                tweet_data['media'] = media_urls
                
                tweets.append(tweet_data)
                
            except Exception as e:
                print(f"Error extracting tweet data: {e}")
                continue
        
        print(f"Extracted {len(tweets)} tweets")
        return tweets
    
    def filter_recent_tweets(self, tweets: List[Dict], hours: int = 24) -> List[Dict]:
        """Filter tweets to only include ones from the past N hours."""
        cutoff_time = datetime.now(self.timezone) - timedelta(hours=hours)
        recent_tweets = []
        
        for tweet in tweets:
            if tweet.get('timestamp'):
                # Convert timestamp to timezone-aware datetime if needed
                tweet_time = tweet['timestamp']
                if tweet_time.tzinfo is None:
                    tweet_time = self.timezone.localize(tweet_time)
                
                if tweet_time >= cutoff_time:
                    recent_tweets.append(tweet)
            else:
                # If no timestamp, include it (better safe than sorry)
                recent_tweets.append(tweet)
        
        print(f"Filtered to {len(recent_tweets)} tweets from the past {hours} hours")
        return recent_tweets
    
    async def scrape_liked_tweets(self, num_scrolls: int = 5, hours_filter: int = 24) -> List[Dict]:
        """Main scraping function."""
        async with async_playwright() as p:
            # Launch browser with persistent context
            browser = await p.chromium.launch(headless=False)  # Set to True for production
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # Load cookies
                if not await self.load_cookies(context):
                    print("Failed to load cookies. Cannot proceed without authentication.")
                    return []
                
                # Navigate to likes page (this will automatically use the loaded cookies)
                if not await self.navigate_to_likes(page):
                    print("Failed to navigate to likes page or session expired.")
                    return []
                
                # Scroll to load more tweets
                await self.scroll_and_load_tweets(page, num_scrolls)
                
                # Extract tweet data
                all_tweets = await self.extract_tweet_data(page)
                
                # Filter for recent tweets
                recent_tweets = self.filter_recent_tweets(all_tweets, hours_filter)
                
                return recent_tweets
                
            except Exception as e:
                print(f"Scraping error: {e}")
                return []
            
            finally:
                await browser.close()

async def main():
    """Test the scraper."""
    scraper = TwitterScraper()
    tweets = await scraper.scrape_liked_tweets()
    
    print(f"\nFound {len(tweets)} recent liked tweets:")
    for i, tweet in enumerate(tweets[:5], 1):  # Show first 5
        print(f"\n{i}. {tweet['author_handle']}")
        print(f"   Text: {tweet['text'][:100]}...")
        print(f"   URL: {tweet['url']}")
        print(f"   Time: {tweet['timestamp']}")
        print(f"   Media: {len(tweet['media'])} items")

def get_liked_tweets(num_scrolls: int = 5, hours_filter: int = 24) -> List[Dict]:
    """
    Main function to get liked tweets (for import into tweet_digest.py).
    
    Args:
        num_scrolls: Number of times to scroll the page to load more tweets
        hours_filter: Only return tweets liked in the past N hours
    
    Returns:
        List of tweet dictionaries with keys: text, author_handle, url, timestamp, media
    """
    scraper = TwitterScraper()
    return asyncio.run(scraper.scrape_liked_tweets(num_scrolls, hours_filter))

if __name__ == "__main__":
    asyncio.run(main())