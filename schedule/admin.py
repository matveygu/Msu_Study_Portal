from django.contrib import admin
from .models import Schedule


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['subject', 'faculty', 'group', 'teacher_id', 'time', 'classroom', 'day']
    list_filter = ['subject', 'faculty', 'group', 'teacher_id', 'time', 'classroom', 'day']
    search_fields = ['subject', 'faculty', 'group', 'teacher_id', 'time', 'classroom', 'day']
    readonly_fields = []
    ordering = ['subject', 'faculty', 'group', 'teacher_id', 'time', 'classroom', 'day']