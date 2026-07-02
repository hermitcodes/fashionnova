# users/forms.py
# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomUser, SellerProfile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPES,
        widget=forms.RadioSelect,
        initial='customer'
    )
    store_name = forms.CharField(
        max_length=100,
        required=False,
        label='Store Name',
        help_text='Required only if you are registering as a seller'
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'phone',
            'user_type',
            'password1',
            'password2'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        store_name = cleaned_data.get('store_name')
        
        if user_type == 'seller' and not store_name:
            raise forms.ValidationError("Store name is required for sellers")
        
        return cleaned_data

class UserLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        fields = ['username', 'password']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'address', 'profile_picture']


class ForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your account email'})
    )


class VerifyResetCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label='Verification code',
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit code'})
    )

    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise ValidationError('Code must contain only numbers.')
        return code


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Passwords do not match.')

        if password1:
            validate_password(password1)

        return cleaned_data