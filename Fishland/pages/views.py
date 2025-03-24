from django.shortcuts import render

# Create your views here.

def terms_view(request):
    """Display terms of service page."""
    return render(request, 'pages/terms.html')

def privacy_view(request):
    """Display privacy policy page."""
    return render(request, 'pages/privacy.html')
