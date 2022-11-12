import requests, os, dotenv

dotenv.load_dotenv()


email = "bffs@berkeley.edu"
base = "https://developer.setmore.com/api/v1"


def get_refresh_token():
    refresh_token = os.getenv("REFRESH_TOKEN")
    refresh_token_link = f"{base}/o/oauth2/token?refreshToken={refresh_token}"
    token = requests.get(refresh_token_link).json()["data"]['token']['access_token']
    return token

bearer = get_refresh_token()

def setmore_get(service):
    result = requests.get(url = f'{base}/{service}',headers = { 'Content-Type': 'application/json',
                                                                'Authorization': f'Bearer {bearer}'
                                                              })
    try:
        return result.json()["data"]
    except Exception:
        print(service)
        return result.json()
    
  


def get_services():
    return setmore_get("bookingpage/services")

def get_staff():
    return setmore_get("bookingapi/staffs")

def get_appointments(start, end):
    return setmore_get(f"bookingapi/appointments?startDate={start}&endDate={end}&customerDetails=true")
