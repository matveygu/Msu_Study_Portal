from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import News
from django.core.exceptions import ValidationError
import os


ALLOWED_NEWS_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.gif',
    '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt'
}

MAX_NEWS_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

class NewsForm(forms.ModelForm):
    def clean_file(self):
        f = self.cleaned_data.get('file')
        if not f:
            return f
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_NEWS_EXTENSIONS:
            raise ValidationError('Недопустимый тип файла для новости')
        if hasattr(f, 'size') and f.size and f.size > MAX_NEWS_FILE_BYTES:
            raise ValidationError('Файл слишком большой (лимит 10 МБ)')
        return f
    class Meta:
        model = News
        fields = ['title', 'content', 'category', 'file', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите заголовок новости'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Введите содержание новости'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Заголовок',
            'content': 'Содержание',
            'category': 'Категория',
            'file': 'Файл',
            'is_published': 'Опубликовать',
        }


class CustomAuthForm(AuthenticationForm):
    username = forms.CharField(
        label='Номер студенческого',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введите номер студенческого'
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введите пароль'
        })
    )
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('student_id', 'faculty', 'course', 'role', 'photo', 'group')