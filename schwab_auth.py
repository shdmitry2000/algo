import os
import base64
import requests
import urllib.parse
import webbrowser
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# ==========================================
# 1. READ APP DETAILS FROM .ENV
# ==========================================
CLIENT_ID = os.getenv('SCHWAB_APP_KEY')
CLIENT_SECRET = os.getenv('SCHWAB_SECRET')
# You must ensure this matches the callback URL in your Schwab Dev Portal App exact settings
REDIRECT_URI = os.getenv('SCHWAB_REDIRECT_URI', 'https://127.0.0.1')

# Schwab OAuth Endpoints
AUTHORIZE_URL = 'https://api.schwabapi.com/v1/oauth/authorize'
TOKEN_URL = 'https://api.schwabapi.com/v1/oauth/token'

def get_authorization_url():
    """Generates the login URL and opens it in your default web browser."""
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI
    }
    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    print("\n[STEP 1] Opening your browser to authorize the app...")
    print(f"If the browser doesn't open automatically, manually go to:\n\n{url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

def get_tokens(auth_code):
    """Exchanges the authorization code for access and refresh tokens."""
    # Create the Authorization header (Base64 encoded "client_id:client_secret")
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # "The 'code' within this request must be URL decoded prior to making the request."
    decoded_code = urllib.parse.unquote(auth_code)
    
    # Constructing raw form data to prevent requests from messing with encoding 
    # (specifically the @ symbol as mentioned in docs)
    raw_data = f"grant_type=authorization_code&code={decoded_code}&redirect_uri={REDIRECT_URI}"
    
    print("\n[STEP 2] Requesting tokens...")
    response = requests.post(TOKEN_URL, headers=headers, data=raw_data)
    
    if response.status_code == 200:
        tokens = response.json()
        print("\n" + "="*50)
        print("SUCCESS! CONNECTION CHECK PASSED!")
        print("="*50 + "\n")
        print("ACCESS TOKEN (valid for 30m):")
        print(tokens.get('access_token')[:50] + "...\n")
        print("REFRESH TOKEN (valid for 7d):")
        print(tokens.get('refresh_token')[:50] + "...\n")
        
        with open('.schwab_tokens.json', 'w') as f:
            f.write(response.text)
        print("Tokens have also been saved to .schwab_tokens.json")
    else:
        print(f"\nERROR: Request failed with status code {response.status_code}")
        print("Response:", response.text)

if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: SCHWAB_APP_KEY and SCHWAB_SECRET must be set in your .env file!")
        exit(1)
        
    print("=== Schwab API Connection Check ===")
    print(f"App Key Loaded:   {CLIENT_ID[:5]}...{CLIENT_ID[-5:]}")
    print(f"App Secret Loaded: {CLIENT_SECRET[:5]}...{CLIENT_SECRET[-5:]}")
    print(f"Redirect URI:     {REDIRECT_URI}")
    print("\n1. We will open the Schwab login page.")
    print("2. You log in and grant access to your accounts.")
    print("3. Schwab will redirect you to your REDIRECT_URI (often looks like a broken page if no server is running).")
    print("4. The URL in your address bar will look like:\n   https://127.0.0.1/?code=AUTHORIZATION_CODE_HERE&session=SESSION_ID_HERE")
    print("5. Copy ONLY the authorization code (the part after code= and before &session=) and paste it below.")
    print("===================================\n")
    
    get_authorization_url()
    
    # Wait for the user to copy-paste the code
    try:
        auth_code_input = input("\nPaste the 'code' parameter from the redirect URL here:\n> ").strip()
        if auth_code_input:
            get_tokens(auth_code_input)
        else:
            print("No code entered. Exiting...")
    except KeyboardInterrupt:
        print("\nConnection check aborted.")
