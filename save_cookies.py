#!/usr/bin/env python3
"""
Twitter Cookie Saver
Interactive script to log in to Twitter and save session cookies for use with scrape_liked_tweets.py
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def save_twitter_cookies():
    """Launch browser, let user log in manually, then save cookies."""
    print("🍪 Twitter Cookie Saver")
    print("=" * 40)
    print("This script will:")
    print("1. Open a browser window")
    print("2. Navigate to Twitter login")
    print("3. Let you log in manually")
    print("4. Save your session cookies to twitter_cookies.json")
    print("\nPress Enter to continue...")
    input()
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode so user can interact
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("\n🌐 Opening Twitter login page...")
            await page.goto('https://twitter.com/i/flow/login')
            
            print("\n👤 Please log in to Twitter in the browser window.")
            print("After logging in successfully:")
            print("- You should see your Twitter home feed")
            print("- Then come back here and press Enter")
            print("\nWaiting for you to log in...")
            input("Press Enter after you've successfully logged in: ")
            
            # Check if login was successful
            current_url = page.url
            print(f"\n🔍 Current URL: {current_url}")
            
            # Look for login success indicators
            login_indicators = [
                '[data-testid="AppTabBar_Home_Link"]',
                '[data-testid="SideNav_AccountSwitcher_Button"]',
                '[data-testid="primaryColumn"]',
                '[aria-label="Home timeline"]'
            ]
            
            logged_in = False
            for indicator in login_indicators:
                element = await page.query_selector(indicator)
                if element:
                    logged_in = True
                    break
            
            if not logged_in and 'login' not in current_url:
                # Try navigating to home to verify login
                print("🏠 Verifying login by navigating to home...")
                await page.goto('https://twitter.com/home')
                await page.wait_for_timeout(3000)
                
                for indicator in login_indicators:
                    element = await page.query_selector(indicator)
                    if element:
                        logged_in = True
                        break
            
            if not logged_in:
                print("❌ Login verification failed.")
                print("Please make sure you're properly logged in and try again.")
                return False
            
            print("✅ Login verified successfully!")
            
            # Get all cookies
            cookies = await context.cookies()
            
            if not cookies:
                print("❌ No cookies found. Something went wrong.")
                return False
            
            # Filter for Twitter-related cookies (optional - you can save all)
            twitter_cookies = [
                cookie for cookie in cookies 
                if 'twitter.com' in cookie.get('domain', '') or 'x.com' in cookie.get('domain', '')
            ]
            
            if not twitter_cookies:
                print("⚠️  No Twitter-specific cookies found, saving all cookies instead...")
                twitter_cookies = cookies
            
            # Save cookies to file
            with open('twitter_cookies.json', 'w') as f:
                json.dump(twitter_cookies, f, indent=2)
            
            print(f"\n💾 Saved {len(twitter_cookies)} cookies to twitter_cookies.json")
            print("✨ You can now use scrape_liked_tweets.py!")
            
            # Show some cookie info (without sensitive data)
            print(f"\n📊 Cookie summary:")
            for cookie in twitter_cookies[:3]:  # Show first 3 cookies
                print(f"  - {cookie['name']}: {cookie['domain']}")
            if len(twitter_cookies) > 3:
                print(f"  ... and {len(twitter_cookies) - 3} more")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False
            
        finally:
            print("\n🔒 Closing browser...")
            await browser.close()

async def main():
    """Main function."""
    try:
        success = await save_twitter_cookies()
        if success:
            print("\n🎉 Cookie saving completed successfully!")
            print("\nNext steps:")
            print("1. Run: python scrape_liked_tweets.py")
            print("2. The scraper will now use your saved session")
            print("3. Re-run this script if your session expires")
        else:
            print("\n💔 Cookie saving failed. Please try again.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())