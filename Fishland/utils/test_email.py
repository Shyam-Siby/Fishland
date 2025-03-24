from django.core.mail import send_mail
from django.conf import settings

def test_email_configuration():
    try:
        send_mail(
            subject='FISHLAND Email Test',
            message='This is a test email to verify the email configuration is working.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        return True, "Test email sent successfully!"
    except Exception as e:
        return False, f"Error sending test email: {str(e)}"
