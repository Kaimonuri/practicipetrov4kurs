from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import RegisterForm


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


@login_required
def profile(request):
    orders = request.user.orders.prefetch_related('items__product').all()
    return render(request, 'accounts/profile.html', {'orders': orders})
