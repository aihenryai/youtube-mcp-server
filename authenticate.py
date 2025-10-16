#!/usr/bin/env python3
"""
OAuth2 Authentication CLI Tool
Helper script for YouTube MCP Server authentication
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auth import OAuth2Manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description='OAuth2 Authentication Manager for YouTube MCP Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Authenticate with full access
  python authenticate.py auth

  # Authenticate with specific scopes
  python authenticate.py auth --scope readonly

  # Check authentication status
  python authenticate.py status

  # Revoke authentication
  python authenticate.py revoke

Scopes:
  readonly - Read-only access to YouTube data
  upload   - Upload videos
  full     - Full access (default)
"""
    )
    
    parser.add_argument(
        'command',
        choices=['auth', 'status', 'revoke', 'test'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--scope',
        choices=['readonly', 'upload', 'full'],
        default='full',
        help='OAuth2 scope level (default: full)'
    )
    
    parser.add_argument(
        '--credentials',
        default='credentials.json',
        help='Path to OAuth2 credentials file'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-authentication'
    )
    
    args = parser.parse_args()
    
    # Initialize OAuth2 Manager
    try:
        scopes = OAuth2Manager.SCOPES[args.scope]
        oauth = OAuth2Manager(
            credentials_file=args.credentials,
            scopes=scopes
        )
    except FileNotFoundError as e:
        logger.error(f"\n❌ {e}")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Failed to initialize OAuth2: {e}")
        return 1
    
    # Execute command
    if args.command == 'auth':
        return authenticate(oauth, args.force)
    elif args.command == 'status':
        return show_status(oauth)
    elif args.command == 'revoke':
        return revoke(oauth)
    elif args.command == 'test':
        return test_connection(oauth)
    
    return 0


def authenticate(oauth: OAuth2Manager, force: bool = False) -> int:
    """Run authentication flow"""
    try:
        logger.info("\n🔐 Starting OAuth2 authentication...")
        logger.info("=" * 60)
        
        if not force and oauth.token_storage.exists():
            logger.info("📝 Existing token found, checking validity...")
        
        creds = oauth.authorize(force_reauth=force)
        
        # Show token info
        info = oauth.get_token_info()
        
        logger.info("\n✅ Authentication successful!")
        logger.info("=" * 60)
        logger.info(f"Valid: {info['valid']}")
        logger.info(f"Has refresh token: {info['has_refresh_token']}")
        logger.info(f"Scopes: {', '.join(info['scopes'])}")
        
        if info['expiry']:
            logger.info(f"Expires: {info['expiry']}")
        
        logger.info("\n💡 Your YouTube MCP Server is now authenticated!")
        logger.info("   You can use all playlist management features.")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Authentication failed: {e}")
        return 1


def show_status(oauth: OAuth2Manager) -> int:
    """Show authentication status"""
    try:
        info = oauth.get_token_info()
        
        logger.info("\n📊 Authentication Status")
        logger.info("=" * 60)
        
        if not info['authenticated']:
            logger.info("❌ Not authenticated")
            logger.info("\n💡 Run: python authenticate.py auth")
            return 1
        
        logger.info(f"✅ Authenticated: {info['authenticated']}")
        logger.info(f"   Valid: {info['valid']}")
        logger.info(f"   Expired: {info['expired']}")
        logger.info(f"   Has refresh token: {info['has_refresh_token']}")
        
        if info['expiry']:
            logger.info(f"\n⏰ Token Expiry: {info['expiry']}")
            if info['time_until_expiry_seconds']:
                hours = info['time_until_expiry_seconds'] / 3600
                logger.info(f"   Time remaining: {hours:.1f} hours")
        
        logger.info(f"\n🔑 Scopes:")
        for scope in info['scopes']:
            logger.info(f"   - {scope}")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Failed to get status: {e}")
        return 1


def revoke(oauth: OAuth2Manager) -> int:
    """Revoke authentication"""
    try:
        logger.info("\n⚠️  Revoking authentication...")
        
        # Confirm
        response = input("Are you sure? This will delete your token. (y/N): ")
        if response.lower() != 'y':
            logger.info("Cancelled.")
            return 0
        
        oauth.revoke_credentials()
        
        logger.info("\n✅ Authentication revoked successfully")
        logger.info("   Token file deleted")
        logger.info("\n💡 To re-authenticate, run: python authenticate.py auth")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Failed to revoke: {e}")
        return 1


def test_connection(oauth: OAuth2Manager) -> int:
    """Test connection to YouTube API"""
    try:
        logger.info("\n🧪 Testing YouTube API connection...")
        logger.info("=" * 60)
        
        # Get authenticated service
        youtube = oauth.get_authenticated_service()
        
        # Make a simple API call
        logger.info("Fetching your channel info...")
        response = youtube.channels().list(
            part='snippet,statistics',
            mine=True
        ).execute()
        
        if not response.get('items'):
            logger.warning("⚠️  No channel found for this account")
            return 1
        
        channel = response['items'][0]
        snippet = channel['snippet']
        stats = channel.get('statistics', {})
        
        logger.info("\n✅ Connection successful!")
        logger.info("=" * 60)
        logger.info(f"Channel: {snippet['title']}")
        logger.info(f"Subscribers: {stats.get('subscriberCount', 'Hidden')}")
        logger.info(f"Videos: {stats.get('videoCount', 0)}")
        logger.info(f"Views: {stats.get('viewCount', 0)}")
        
        logger.info("\n💡 Your YouTube MCP Server is ready to use!")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Connection test failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
