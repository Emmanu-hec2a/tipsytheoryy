import requests
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
import os
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class MpesaIntegration:

    def __init__(self):

        self.consumer_key = os.environ.get('MPESA_CONSUMER_KEY')
        self.consumer_secret = os.environ.get('MPESA_CONSUMER_SECRET')
        self.passkey = os.environ.get('MPESA_PASSKEY')

        self.paybill_number = os.environ.get('MPESA_PAYBILL_NUMBER')
        self.till_number = os.environ.get('MPESA_TILL_NUMBER')

        is_production = os.environ.get('MPESA_PRODUCTION', 'false').lower() == 'true'

        self.base_url = (
            'https://api.safaricom.co.ke'
            if is_production
            else 'https://sandbox.safaricom.co.ke'
        )

        self.access_token_url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        self.stk_push_url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
        self.stk_query_url = f'{self.base_url}/mpesa/stkpushquery/v1/query'

    # =========================
    # ACCESS TOKEN
    # =========================
    def get_access_token(self):
        token = cache.get('mpesa_access_token')
        if token:
            return token

        try:
            response = requests.get(
                self.access_token_url,
                auth=(self.consumer_key, self.consumer_secret),
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            token = data['access_token']
            cache.set('mpesa_access_token', token, timeout=3500)

            return token

        except Exception:
            logger.exception("Failed to obtain MPESA access token")
            return None

    # =========================
    # PASSWORD GENERATION
    # =========================
    def generate_password(self, shortcode, timestamp):
        data_to_encode = f"{shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode()

    # =========================
    # STK PUSH
    # =========================
    def initiate_stk_push(self, phone_number, amount, account_reference,
                          transaction_desc, store_type='liquor'):

        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Access token error'}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        if store_type == 'liquor':
            shortcode = self.paybill_number
            transaction_type = "CustomerPayBillOnline"
            account_ref = account_reference
        else:
            shortcode = self.till_number
            transaction_type = "CustomerBuyGoodsOnline"
            account_ref = account_reference[:12]

        password = self.generate_password(shortcode, timestamp)

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": transaction_type,
            "Amount": int(Decimal(str(amount))),
            "PartyA": phone_number,
            "PartyB": shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
            "AccountReference": account_ref,
            "TransactionDesc": transaction_desc[:13]
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            logger.info(f"""
            ===== SANDBOX DEBUG =====
            Shortcode: {shortcode}
            Phone: {phone_number}
            Amount: {amount}
            Callback: {"https://sandbox.safaricom.co.ke/mpesa/"}
            Base URL: {self.base_url}
            =========================
            """)

            response = requests.post(
                self.stk_push_url,
                json=payload,
                headers=headers,
                timeout=20
            )

            # response.raise_for_status()
            result = response.json()
            logger.info(f"MPESA RAW RESPONSE: {result}")

            if response.status_code != 200:
                logger.error(f"STK ERROR {response.status_code}: {result}")
                return {
                    "success": False,
                    "message": result
                }

            if result.get("ResponseCode") == "0":
                return {
                    "success": True,
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "customer_message": result.get("CustomerMessage")
                }

            return {
                "success": False,
                "message": result.get("ResponseDescription", "STK push failed")
            }

        except requests.exceptions.RequestException:
            logger.exception("STK Push network error")
            return {"success": False, "message": "Network error"}

    # =========================
    # STK QUERY
    # =========================
    def query_stk_status(self, checkout_request_id):

        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Access token error'}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        shortcode = self.paybill_number  # or till, depending on your logic
        password = self.generate_password(shortcode, timestamp)

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.stk_query_url,
                json=payload,
                headers=headers,
                timeout=20
            )

            response.raise_for_status()
            result = response.json()

            return {
                "success": True,
                "response_code": result.get("ResponseCode"),
                "result_code": result.get("ResultCode"),
                "result_desc": result.get("ResultDesc")
            }

        except requests.exceptions.RequestException:
            logger.exception("STK Query error")
            return {"success": False, "message": "Query network error"}

    # =========================
    # PHONE FORMATTER
    # =========================
    def format_phone_number(self, phone_number):

        phone = ''.join(filter(str.isdigit, str(phone_number)))

        if phone.startswith('0') and len(phone) == 10:
            return '254' + phone[1:]
        elif phone.startswith('254') and len(phone) == 12:
            return phone
        elif len(phone) == 9:
            return '254' + phone
        else:
            raise ValueError("Invalid phone number format")
        
mpesa = MpesaIntegration()