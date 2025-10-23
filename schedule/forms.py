from django import forms
from .models import Homework


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ['content', 'file', 'due_date']  # ⚡ assigned_date не показываем пользователю

        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Введите текст задания...'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'content': 'Текст задания',
            'file': 'Файл (необязательно)',
            'due_date': 'Срок сдачи',
        }
