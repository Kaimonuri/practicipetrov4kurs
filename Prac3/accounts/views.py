from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import RegisterForm, USERNAME_RE


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'

    def form_invalid(self, form):
        messages.error(self.request, 'Неверный логин или пароль.')
        return super().form_invalid(form)


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Регистрация завершена. Теперь войдите в аккаунт.')
            return redirect('accounts:login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def validate_username(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'valid': False, 'message': 'Введите логин.'})
    if not USERNAME_RE.fullmatch(username):
        return JsonResponse({
            'valid': False,
            'message': 'Только латинские буквы и цифры, минимум 6 символов.',
        })
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'valid': False, 'message': 'Такой логин уже занят.'})
    return JsonResponse({'valid': True, 'message': 'Логин свободен.'})


@login_required
def profile(request):
    orders = request.user.orders.prefetch_related('items__product').all()
    profile_obj = getattr(request.user, 'profile', None)
    return render(request, 'accounts/profile.html', {
        'orders': orders,
        'profile_obj': profile_obj,
    })
