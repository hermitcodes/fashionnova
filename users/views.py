# users/views.py
# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from .forms import (
    UserRegisterForm,
    UserLoginForm,
    UserUpdateForm,
    ForgotPasswordEmailForm,
    VerifyResetCodeForm,
    ResetPasswordForm,
)
from .models import SellerProfile, PasswordResetCode
from fashionnova_app.models import Order

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # Create user
            user = form.save(commit=False)
            user.email = form.cleaned_data.get('email')
            user.phone = form.cleaned_data.get('phone')
            user.user_type = form.cleaned_data.get('user_type')
            user.save()
            
            # If user is seller, create seller profile
            if user.user_type == 'seller':
                store_name = form.cleaned_data.get('store_name')
                SellerProfile.objects.create(
                    user=user,
                    store_name=store_name,
                    business_registration='',
                    description=''
                )
            
            # Login user
            login(request, user)
            
            # Show success message
            if user.user_type == 'seller':
                messages.success(request, f'Your seller account has been created! Welcome to FashionNova!')
                return redirect('seller_dashboard')
            else:
                messages.success(request, f'Your account has been created! Welcome to FashionNova!')
                return redirect('home')
    else:
        form = UserRegisterForm()
    
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect based on user type
                if user.user_type == 'seller':
                    return redirect('seller_dashboard')
                else:
                    return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'users/profile.html', {'form': form})


@login_required
def customer_orders_dashboard_view(request):
    """Customer dashboard page to track their own order statuses."""
    if request.user.user_type == 'seller':
        return redirect('seller_orders')

    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items', 'items__product'
    ).order_by('-created_at')

    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'users/customer_orders_dashboard.html', context)


def forgot_password_request_view(request):
    if request.method == 'POST':
        form = ForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            user = User.objects.filter(email__iexact=email).first()

            if not user:
                messages.error(request, 'No account exists with that email address.')
                return render(request, 'users/forgot_password.html', {'form': form})

            PasswordResetCode.objects.filter(email__iexact=email, is_used=False).update(is_used=True)
            code = f"{random.randint(0, 999999):06d}"
            PasswordResetCode.objects.create(
                email=email,
                code=code,
                expires_at=timezone.now() + timedelta(minutes=10)
            )

            send_mail(
                subject='FashionNova Password Reset Code',
                message=(
                    f'Hello {user.username},\n\n'
                    f'Your password reset code is: {code}\n'
                    'This code expires in 10 minutes.\n\n'
                    'If you did not request this, you can ignore this email.'
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@fashionnova.local'),
                recipient_list=[email],
                fail_silently=False,
            )

            request.session['password_reset_email'] = email
            request.session['password_reset_verified'] = False
            messages.success(request, 'Verification code sent to your email.')
            return redirect('verify_reset_code')
    else:
        form = ForgotPasswordEmailForm()

    return render(request, 'users/forgot_password.html', {'form': form})


def verify_reset_code_view(request):
    reset_email = request.session.get('password_reset_email')
    if not reset_email:
        messages.error(request, 'Start password reset again.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = VerifyResetCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            reset_code = PasswordResetCode.objects.filter(
                email__iexact=reset_email,
                code=code,
                is_used=False,
            ).order_by('-created_at').first()

            if not reset_code:
                messages.error(request, 'Invalid verification code.')
            elif reset_code.is_expired():
                reset_code.is_used = True
                reset_code.save(update_fields=['is_used'])
                messages.error(request, 'Code expired. Request a new one.')
                return redirect('forgot_password')
            else:
                reset_code.is_used = True
                reset_code.save(update_fields=['is_used'])
                request.session['password_reset_verified'] = True
                messages.success(request, 'Code verified. Set your new password.')
                return redirect('reset_password')
    else:
        form = VerifyResetCodeForm()

    return render(request, 'users/verify_reset_code.html', {'form': form, 'email': reset_email})


def reset_password_view(request):
    reset_email = request.session.get('password_reset_email')
    verified = request.session.get('password_reset_verified', False)

    if not reset_email or not verified:
        messages.error(request, 'Verify your code before setting a new password.')
        return redirect('forgot_password')

    user = User.objects.filter(email__iexact=reset_email).first()
    if not user:
        messages.error(request, 'Account not found. Try again.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.save(update_fields=['password'])

            request.session.pop('password_reset_email', None)
            request.session.pop('password_reset_verified', None)
            messages.success(request, 'Password updated successfully. Please log in.')
            return redirect('login')
    else:
        form = ResetPasswordForm()

    return render(request, 'users/reset_password.html', {'form': form})