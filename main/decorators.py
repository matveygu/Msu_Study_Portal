from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

def headman_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.role in ['headman', 'teacher', 'admin'],
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def teacher_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.role in ['teacher', 'admin'],
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def admin_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.role == 'admin',
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator