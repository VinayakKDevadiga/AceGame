from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import get_connection

def send_email_with_fallback(subject, message, recipient_list, html_message=None):
    accounts = settings.EMAIL_ACCOUNTS

    # Try primary account
    try:
        connection = get_connection(
            host=accounts['primary']['HOST'],
            port=accounts['primary']['PORT'],
            username=accounts['primary']['USER'],
            password=accounts['primary']['PASSWORD'],
            use_tls=accounts['primary']['USE_TLS']
        )
        send_mail(
            subject,
            message,
            accounts['primary']['FROM'],
            recipient_list,
            connection=connection,
            fail_silently=False,
            html_message=html_message,  # ✅ added here
        )
        return True
    except Exception as e:
        print(f"Primary email failed: {e}")

    # Try secondary account
    try:
        connection = get_connection(
            host=accounts['secondary']['HOST'],
            port=accounts['secondary']['PORT'],
            username=accounts['secondary']['USER'],
            password=accounts['secondary']['PASSWORD'],
            use_tls=accounts['secondary']['USE_TLS']
        )
        send_mail(
            subject,
            message,
            accounts['secondary']['FROM'],
            recipient_list,
            connection=connection,
            fail_silently=False,
            html_message=html_message,  # ✅ added here
        )
        return True
    except Exception as e:
        print(f"Secondary email failed: {e}")

    return False
