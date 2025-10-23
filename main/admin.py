from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import CustomUser, Group


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'student_id', 'faculty', 'course', 'role', 'group')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = '__all__'


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ['username', 'email', 'first_name', 'last_name', 'student_id',
                    'faculty', 'course', 'role', 'group', 'is_staff']
    list_filter = ['faculty', 'course', 'role', 'group', 'is_staff', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'student_id']

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Персональная информация', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Учебная информация', {
            'fields': ('student_id', 'faculty', 'course', 'role', 'group', 'photo')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Важные даты', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email',
                       'student_id', 'faculty', 'course', 'role', 'group'),
        }),
    )

    ordering = ['faculty', 'course', 'last_name']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'faculty', 'course', 'student_count']
    list_filter = ['faculty', 'course']
    search_fields = ['name', 'faculty']
    ordering = ['faculty', 'course', 'name']

    def student_count(self, obj):
        return obj.customuser_set.count()

    student_count.short_description = 'Количество студентов'