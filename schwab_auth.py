import base64
import requests
import urllib.parse
import webbrowser

# ==========================================
# 1. FILL IN YOUR APP DETAILS HERE
# ==========================================
CLIENT_ID = 'YOUR_CLIENT_ID'          # Also called App Key
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'  # Also called App Secret
REDIRECT_URI = 'https://127.0.0.1'    # Must be exactly what you put in the Dev Portal

# Schwab OAuth Endpoints
AUTHORIZE_URL = 'https://api.schwab.com/v1/oauth/authorize'
TOKEN_URL = 'https://api.schwab.com/v1/oauth/token'

def get_authorization_url():
    """Generates the login URL and opens it in your default web browser."""
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code'
    }
    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    print("\n[STEP 1] Opening your browser to authorize the app...")
    print(f"If the browser doesn't open, manually go to:\n{url}\n")
    webbrowser.open(url)
    
def get_tokens(auth_code):
    """Exchanges the authorization code for access and refresh tokens."""
    # Create the Authorization header (Base64 encoded "client_id:client_secret")
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
    
    print("\n[STEP 2] Requesting tokens...")
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        print("\nSUCCESS! Here are your tokens:\n")
        print("ACCESS TOKEN (valid for 30m):")
        print(tokens.get('access_token'), "\n")
        print("REFRESH TOKEN (valid for 7d):")
        print(tokens.get('refresh_token'), "\n")
        
        # Consider saving these to a file or environment variables
        with open('.schwab_tokens.json', 'w') as f:
            f.write(response.text)
        print("Tokens have also been saved to .schwab_tokens.json")
    else:
        print(f"\nERROR: Request failed with status code {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    if CLIENT_ID == 'YOUR_CLIENT_ID':
        print("Please edit this file and fill in your CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI.")
        exit(1)
        
    print("=== Schwab API Authentication ===")
    print("1. We will open the Schwab login page.")
    print("2. You log in and grant access.")
    print("3. Schwab will redirect you to your REDIRECT_URI.")
    print("4. The URL will look like: https://127.0.0.1/?code=AUTHORIZATION_CODE_HERE")
    print("5. Copy ONLY the authorization code and paste it below.")
    print("=================================")
    
    get_authorization_url()
    
    # Wait for the user to copy-paste the code
    auth_code = input("\nPaste the 'code' parameter from the redirect URL here:\n> ").strip()
    
    # Standardize the code (sometimes URL encoding causes issues if copy-pasted directly)
    auth_code = urllib.parse.unquote(auth_code)
    
    get_tokens(auth_code)
