from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, FileResponse
from django.conf import settings
import os
from .models import Material, MaterialFolder
from .forms import MaterialUploadForm, MaterialEditForm


def is_headman_or_above(user):
    return user.role in ['headman', 'teacher', 'admin']

def is_teacher_or_admin(user):
    return user.role in ['teacher', 'admin']


@login_required
def materials_view(request):
    """Redirect legacy materials landing to Drive root"""
    return redirect('materials_drive_root')


@login_required
def legacy_materials_redirect(request, *args, **kwargs):
    """Unified redirect for all legacy material URLs"""
    return redirect('materials_drive_root')


@login_required
@user_passes_test(is_teacher_or_admin)
def upload_material(request):
    if request.method == 'POST':
        form = MaterialUploadForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.uploaded_by = request.user

            # Создаем папку если указана новая
            folder_name = request.POST.get('new_folder', '').strip()
            if folder_name:
                parent_id = request.POST.get('folder') or request.GET.get('folder') or request.session.get('selected_folder_id')
                parent_folder = None
                if parent_id:
                    try:
                        parent_folder = MaterialFolder.objects.get(id=parent_id)
                    except MaterialFolder.DoesNotExist:
                        parent_folder = None
                folder, created = MaterialFolder.objects.get_or_create(
                    name=folder_name,
                    defaults={
                        'created_by': request.user,
                    }
                )
                if parent_folder and folder.parent_folder_id is None:
                    folder.parent_folder = parent_folder
                    folder.save(update_fields=['parent_folder'])
                material.folder = folder

            # Если папка не выбрана явно, использовать выбранную папку из сессии
            if not material.folder_id:
                selected_id = request.POST.get('folder') or request.GET.get('folder') or request.session.get('selected_folder_id')
                if selected_id:
                    try:
                        material.folder = MaterialFolder.objects.get(id=selected_id)
                    except MaterialFolder.DoesNotExist:
                        pass

            material.save()
            messages.success(request, "Материал успешно загружен")
            redirect_folder = request.POST.get('folder') or request.GET.get('folder') or request.session.get('selected_folder_id')
            if redirect_folder:
                return redirect('materials_drive_folder', folder_id=redirect_folder)
            return redirect('materials_drive_root')
    else:
        # Предзаполнить форму выбранной папкой из GET или сессии
        selected_folder = None
        selected_id = request.GET.get('folder') or request.session.get('selected_folder_id')
        if selected_id:
            try:
                selected_folder = MaterialFolder.objects.get(id=selected_id)
            except MaterialFolder.DoesNotExist:
                selected_folder = None
        initial = {
        }
        if selected_folder:
            initial['folder'] = selected_folder.id
        form = MaterialUploadForm(initial=initial)

    # Получаем доступные папки для выбора
    folders = MaterialFolder.objects.all()

    context = {
        'form': form,
        'folders': folders,
        'selected_folder': selected_folder if 'selected_folder' in locals() else None,
    }
    return render(request, 'upload.html', context)


@login_required
def download_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    file_path = os.path.join(settings.MEDIA_ROOT, str(material.file))

    if material.file:
        filename = os.path.basename(material.file.name)
        response = FileResponse(material.file.open(), as_attachment=True)
        response['Content-Disposition'] = (
            f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}"
        )
        return response
    else:
        messages.error(request, "Файл не найден")
        return HttpResponse("Файл не найден", status=404)

@login_required
@user_passes_test(is_teacher_or_admin)
def delete_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    if request.method == 'POST':
        if material.file:
            try:
                material.file.storage.delete(material.file.name)
            except Exception:
                pass
        material.delete()
        messages.success(request, 'Домашка успешно удалена')
    return redirect(f'/materials')


@login_required
@user_passes_test(is_teacher_or_admin)
def edit_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    if request.method == 'POST':
        form = MaterialEditForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            # If replace_file is False, keep existing file
            replace = form.cleaned_data.get('replace_file')
            if not replace and 'file' in form.changed_data:
                material.file = material.__class__.objects.get(pk=material.pk).file
            form.save()
            messages.success(request, 'Материал обновлён')
            # Redirect back to current folder if any
            redirect_folder = material.folder_id or request.session.get('selected_folder_id')
            if redirect_folder:
                return redirect('materials_drive_folder', folder_id=redirect_folder)
            return redirect('materials_drive_root')
    else:
        form = MaterialEditForm(instance=material)
    return render(request, 'edit_material.html', {'form': form, 'material': material})


@login_required
@user_passes_test(is_teacher_or_admin)
def rename_folder(request, folder_id):
    folder = get_object_or_404(MaterialFolder, id=folder_id)
    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if new_name:
            folder.name = new_name
            folder.save(update_fields=['name'])
            messages.success(request, 'Папка переименована')
        else:
            messages.error(request, 'Название папки не может быть пустым')
        parent_id = folder.parent_folder_id
        return redirect('materials_drive_folder', folder_id=(parent_id or folder.id))
    # GET -> show edit form
    return render(request, 'edit_folder.html', {'folder': folder})


@login_required
@user_passes_test(is_teacher_or_admin)
def delete_folder(request, folder_id):
    folder = get_object_or_404(MaterialFolder, id=folder_id)
    parent_id = folder.parent_folder_id
    if request.method == 'POST':
        # Delete all materials in this folder (files removed via Material delete)
        Material.objects.filter(folder=folder).delete()
        folder.delete()
        messages.success(request, 'Папка удалена')
        if parent_id:
            return redirect('materials_drive_folder', folder_id=parent_id)
        return redirect('materials_drive_root')
    # GET confirm page
    return render(request, 'delete_folder.html', {'folder': folder, 'parent_id': parent_id})


@login_required
@user_passes_test(is_teacher_or_admin)
def edit_folder(request, folder_id):
    folder = get_object_or_404(MaterialFolder, id=folder_id)
    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if new_name:
            folder.name = new_name
            folder.save(update_fields=['name'])
            messages.success(request, 'Папка обновлена')
            return redirect('materials_drive_folder', folder_id=folder.id)
        messages.error(request, 'Название папки не может быть пустым')
    return render(request, 'edit_folder.html', {'folder': folder})


# Drive-like browsing
@login_required
def drive_root(request):
    # Show top-level folders for user's faculty and course, and uncategorized materials

    # Clear selected folder at root
    request.session['selected_folder_id'] = None

    folders_qs = MaterialFolder.objects.filter(parent_folder__isnull=True)
    materials_qs = Material.objects.filter(folder__isnull=True)

    context = {
        'current_folder': None,
        'subfolders': folders_qs.order_by('name'),
        'materials': materials_qs.order_by('-upload_date'),
        'breadcrumbs': [],
        'can_manage': is_teacher_or_admin(request.user),
        'current_selected_folder': None,
    }
    return render(request, 'drive.html', context)


@login_required
def drive_folder(request, folder_id: int):
    folder = get_object_or_404(MaterialFolder, id=folder_id)
    # Persist current folder selection in session
    request.session['selected_folder_id'] = folder.id
    subfolders = MaterialFolder.objects.filter(parent_folder=folder).order_by('name')
    materials = Material.objects.filter(folder=folder).order_by('-upload_date')

    # Build breadcrumbs up the tree
    breadcrumbs = []
    current = folder
    while current is not None:
        breadcrumbs.append(current)
        current = current.parent_folder
    breadcrumbs.reverse()

    context = {
        'current_folder': folder,
        'subfolders': subfolders,
        'materials': materials,
        'breadcrumbs': breadcrumbs,
        'can_manage': is_teacher_or_admin(request.user),
        'current_selected_folder': folder,
    }
    return render(request, 'drive.html', context)


@login_required
@user_passes_test(is_teacher_or_admin)
def create_folder(request, parent_id: int = None):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        parent_folder = None
        if parent_id:
            parent_folder = get_object_or_404(MaterialFolder, id=parent_id)
        else:
            selected_id = request.session.get('selected_folder_id')
            if selected_id:
                parent_folder = get_object_or_404(MaterialFolder, id=selected_id)

        if not name:
            messages.error(request, 'Введите название папки')
            if parent_folder:
                return redirect('materials_drive_folder', folder_id=parent_folder.id)
            return redirect('materials_drive_root')

        folder = MaterialFolder.objects.create(
            name=name,
            parent_folder=parent_folder,
            created_by=request.user,
        )
        messages.success(request, 'Папка создана')
        return redirect('materials_drive_folder', folder_id=folder.id)

    # GET fallback
    if parent_id:
        return redirect('materials_drive_folder', folder_id=parent_id)
    return redirect('materials_drive_root')