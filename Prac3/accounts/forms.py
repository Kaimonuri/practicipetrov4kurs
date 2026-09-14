import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


USERNAME_RE = re.compile(r'^[A-Za-z0-9]{6,}$')
FULL_NAME_RE = re.compile(r'^[А-Яа-яЁё]+(?: [А-Яа-яЁё]+)+$')
PHONE_RE = re.compile(r'^8\(\d{3}\)\d{3}-\d{2}-\d{2}$')


class RegisterForm(UserCreationForm):
    username = forms.CharField(
        label='Логин',
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'username',
            'pattern': '[A-Za-z0-9]{6,}',
            'minlength': '6',
        }),
    )
    full_name = forms.CharField(
        label='ФИО',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович',
            'autocomplete': 'name',
        }),
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '8(999)123-45-67',
            'inputmode': 'tel',
            'autocomplete': 'tel',
        }),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'full_name', 'phone', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Повторите пароль'
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'minlength': '8',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'new-password',
            'minlength': '8',
        })

    def clean_username(self):
        username = self.cleaned_data['username']
        if not USERNAME_RE.fullmatch(username):
            raise forms.ValidationError(
                'Логин должен содержать только латинские буквы и цифры и быть не короче 6 символов.'
            )
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Такой логин уже занят.')
        return username

    def clean_full_name(self):
        full_name = ' '.join(self.cleaned_data['full_name'].split())
        if not FULL_NAME_RE.fullmatch(full_name):
            raise forms.ValidationError('ФИО должно содержать только кириллицу и пробелы.')
        return full_name

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not PHONE_RE.fullmatch(phone):
            raise forms.ValidationError('Введите телефон в формате 8(XXX)XXX-XX-XX.')
        return phone

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        if len(password) < 8:
            raise forms.ValidationError('Пароль должен содержать не менее 8 символов.')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data['full_name']
        parts = full_name.split()
        user.last_name = parts[0] if parts else ''
        user.first_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'phone': self.cleaned_data['phone'],
                },
            )
        return user
