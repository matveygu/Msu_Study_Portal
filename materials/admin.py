from django.contrib import admin
from .models import Material, MaterialFolder


@admin.register(MaterialFolder)
class MaterialFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'faculty', 'course', 'subject', 'parent_folder', 'created_by', 'created_at']
    list_filter = ['faculty', 'course', 'subject', 'created_at']
    search_fields = ['name', 'faculty', 'subject', 'created_by__username']
    readonly_fields = ['created_at']
    ordering = ['faculty', 'course', 'subject', 'name']


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'faculty', 'course', 'subject', 'type', 'uploaded_by', 'upload_date', 'folder']
    list_filter = ['faculty', 'course', 'subject', 'type', 'upload_date']
    search_fields = ['name', 'subject', 'uploaded_by__username', 'faculty']
    readonly_fields = ['upload_date']
    ordering = ['-upload_date']

    fieldsets = (
        (None, {
            'fields': ('name', 'file', 'faculty', 'course', 'subject', 'type', 'folder')
        }),
        ('Дополнительно', {
            'fields': ('uploaded_by', 'upload_date'),
            'classes': ('collapse',)
        }),
    )