from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLES = [
        ('student', 'Студент'),
        ('headman', 'Староста'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    ]

    student_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Номер студенческого'
    )
    faculty = models.CharField(
        max_length=100,
        verbose_name='Факультет'
    )
    course = models.IntegerField(verbose_name='Курс')
    role = models.CharField(
        max_length=20,
        choices=ROLES,
        default='student',
        verbose_name='Роль'
    )
    photo = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    group = models.ForeignKey(
        'Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Группа'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

    def get_role_display(self):
        return dict(self.ROLES).get(self.role, self.role)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Group(models.Model):
    name = models.CharField(
        max_length=50,
        verbose_name='Название группы'
    )
    faculty = models.CharField(
        max_length=100,
        verbose_name='Факультет'
    )
    course = models.IntegerField(verbose_name='Курс')

    def __str__(self):
        return f"{self.name} ({self.faculty}, {self.course} курс)"

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ['faculty', 'course', 'name']

class News(models.Model):
    CATEGORIES = [
        ('news', 'Новость'),
        ('announcement', 'Объявление'),
        ('event', 'Событие'),
    ]

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержание')
    category = models.CharField(max_length=20, choices=CATEGORIES, default='news', verbose_name='Категория')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Автор')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_published = models.BooleanField(default=True, verbose_name='Опубликовано')
    file = models.FileField(upload_to='news/', blank=True, null=True, verbose_name='Файл')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_short_content(self):
        """Возвращает укороченное содержание (первые 100 символов)"""
        if len(self.content) > 100:
            return self.content[:100] + '...'
        return self.content