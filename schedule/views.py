import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import Schedule, Subject, Homework
from .forms import HomeworkForm


def is_headman_or_above(user):
    return user.role in ['headman', 'teacher', 'admin']


def get_day_name_from_weekday(weekday):
    """Convert weekday number to Russian day name"""
    days_map = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда',
        3: 'Четверг', 4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }
    return days_map.get(weekday, 'Понедельник')


@login_required
def schedule_view(request):
    user_group = request.user.group

    if not user_group and request.user.role != "teacher":
        context = {
            'schedule': [],
            'week_dates': [],
            'current_date': date.today(),
            'error': '❌ У вас не назначена группа. Обратитесь к администратору.'
        }
        return render(request, 'schedule.html', context)

    # Получаем дату из параметра или текущую дату
    current_date_str = request.GET.get('date', date.today().isoformat())
    try:
        current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
    except ValueError:
        current_date = date.today()

    # Вычисляем даты недели
    start_of_week = current_date - timedelta(days=current_date.weekday())
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

    # Даты для навигации
    previous_week = (current_date - timedelta(days=7)).isoformat()
    next_week = (current_date + timedelta(days=7)).isoformat()

    # Получаем день недели для текущей даты
    current_day = get_day_name_from_weekday(current_date.weekday())
    # Расписание на текущий день
    if request.user.role != "teacher":
        schedule = Schedule.objects.filter(
            faculty=request.user.faculty,
            group=user_group,
            day=current_day
        ).order_by('lesson_number')
        homework = Homework.objects.filter(due_date=current_date, group=user_group)
    else:
        schedule = Schedule.objects.filter(
            first_teacher_id=request.user.student_id,
            day=current_day
        ).order_by('lesson_number')
        homework = Homework.objects.filter(due_date=current_date)

    context = {
        'schedule': schedule,
        'week_dates': week_dates,
        'current_date': current_date,
        'current_date_str': current_date.isoformat(),
        'previous_week': previous_week,
        'next_week': next_week,
        'homework': homework,
        'form': HomeworkForm(),
    }
    return render(request, 'schedule.html', context)


@login_required
def day_schedule(request, day):
    """Старая функция для обратной совместимости - перенаправляет на новую систему с датами"""
    # Маппинг старых названий дней на даты текущей недели
    day_mapping = {
        'Понедельник': 0, 'Вторник': 1, 'Среда': 2,
        'Четверг': 3, 'Пятница': 4, 'Суббота': 5
    }

    if day not in day_mapping:
        return redirect('schedule')

    # Вычисляем дату для запрошенного дня
    today = date.today()
    days_difference = day_mapping[day] - today.weekday()
    target_date = today + timedelta(days=days_difference)

    return redirect(f'/schedule/?date={target_date.isoformat()}')


@login_required
@user_passes_test(is_headman_or_above)
def add_homework(request, schedule_id):
    # Получаем дату из параметра или текущую дату
    current_date_str = request.GET.get('date', date.today().isoformat())
    try:
        current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
    except ValueError:
        current_date = date.today()

    # Вычисляем даты недели
    start_of_week = current_date - timedelta(days=current_date.weekday())
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]
    """Добавление домашнего задания для конкретной пары"""
    schedule = get_object_or_404(Schedule, id=schedule_id)

    if request.method == 'POST':
        form = HomeworkForm(request.POST, request.FILES)
        print(form.errors)
        if form.is_valid():
            print("Succes")
            print(schedule.subject)
            homework = form.save(commit=False)
            homework.schedule = schedule
            homework.created_by = request.user
            homework.assigned_date = date.today()  # ⚡ автоматически ставим дату выдачи
            homework.group = schedule.group
            homework.subject = schedule.subject
            homework.save()
            return redirect('schedule_detail', schedule_id=schedule.id)
    else:
        form = HomeworkForm()

    context = {
        'schedule': schedule,
        'week_dates': week_dates,
        'current_date': current_date,
        'current_date_str': current_date.isoformat(),
        'form': form,
    }
    return render(request, 'add_homework.html', context)

@login_required
def download_homework_file(request, schedule_id):
    schedule_item = get_object_or_404(Schedule, id=schedule_id)
    if schedule_item.homework_file:
        response = FileResponse(schedule_item.homework_file.open(), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{schedule_item.homework_file.name}"'
        return response
    else:
        messages.error(request, "Файл не найден")
        return redirect('schedule')


@login_required
def schedule_json(request, day=None):
    user_group = request.user.group

    if not user_group:
        return JsonResponse({'error': 'Group not assigned'}, status=400)

    if day:
        schedule = Schedule.objects.filter(group=user_group, day=day)
    else:
        schedule = Schedule.objects.filter(group=user_group)

    schedule_data = []
    for item in schedule.order_by('day', 'lesson_number'):
        schedule_data.append({
            'day': item.get_day_display(),
            'lesson_number': item.lesson_number,
            'time': item.time,
            'subject': item.subject.name,
            'teacher': item.subject.teacher.get_full_name(),
            'classroom': item.classroom,
            'homework': item.homework,
            'homework_file': item.homework_file.url if item.homework_file else None,
            'homework_date': item.homework_date.isoformat() if item.homework_date else None
        })

    return JsonResponse({'schedule': schedule_data})

@login_required
def schedule_detail(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    homeworks = schedule.homework_assignments.all()
    return render(request, 'schedule_detail.html', {
        'schedule': schedule,
        'homeworks': homeworks
    })

@login_required
@user_passes_test(is_headman_or_above)
def delete_homework(request, schedule_id):
    print(schedule_id)
    schedule = get_object_or_404(Homework, id=schedule_id)
    print(schedule.due_date)
    print(schedule.file)
    if request.method == 'POST':
        if os.path.isfile(f"media/{schedule.file}"):
            os.remove(f"media/{schedule.file}")
        schedule.delete()
        messages.success(request, 'Домашка успешно удалена')
    return redirect(f'/schedule/?date={schedule.due_date}')
