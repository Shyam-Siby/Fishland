# FISHLAND - Bulk Fish Trading Platform

FISHLAND is a comprehensive e-commerce platform for bulk fish trading, connecting sellers with business buyers.

## Features

- Multi-user roles (Admin, Seller, Buyer)
- Product management
- Order processing
- Real-time notifications
- Secure payment integration
- Analytics and reporting
- Inventory management

## Setup Instructions

1. Create and activate virtual environment:
```bash
python -m venv myenv
myenv\Scripts\activate  # On Windows
```

2. Install requirements:
```bash
pip install -r requirements.txt --user
```

3. Create .env file and set up your environment variables:
```
SECRET_KEY=your_secret_key
DEBUG=True
```

4. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Authentication Setup

### Email Configuration

1. For development, the system uses console email backend (emails are printed to console).
2. For production, configure your email settings in `.env`:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=FISHLAND <noreply@fishland.com>
```

### Social Authentication

#### Google OAuth2
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth2 credentials
5. Add to `.env`:
```
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### Facebook OAuth2
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Set up Facebook Login
4. Add to `.env`:
```
FACEBOOK_CLIENT_ID=your-facebook-client-id
FACEBOOK_CLIENT_SECRET=your-facebook-client-secret
```

#### Apple Sign In
1. Go to [Apple Developer](https://developer.apple.com/)
2. Set up Sign in with Apple
3. Add to `.env`:
```
APPLE_CLIENT_ID=your-apple-client-id
APPLE_CLIENT_SECRET=your-apple-client-secret
APPLE_KEY_ID=your-apple-key-id
APPLE_CERTIFICATE_KEY=your-apple-certificate-key
```

### Authentication Features
- Email-based authentication
- Social login (Google, Facebook, Apple)
- Password reset via email
- User registration with email verification
- Separate registration for buyers and sellers
- Profile management
- Session management

## Project Structure

- `core/` - Main Django project configuration
- `accounts/` - User authentication and management
- `products/` - Product listing and management
- `orders/` - Order processing and tracking
- `api/` - REST API endpoints
- `templates/` - HTML templates
- `static/` - Static files (CSS, JS, images)

## Tech Stack

- Backend: Django REST Framework
- Frontend: HTML, CSS, Bootstrap
- Database: SQLite
- Authentication: JWT
- File Storage: Django Storages
