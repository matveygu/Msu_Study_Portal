import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from schedule.models import Subject, Schedule
from main.models import Group, CustomUser
import os
import re
from datetime import *
from django.conf import settings
from django.db import transaction

def parse_teacher_name(full_name):
    """Parse teacher name into first and last name"""
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:]) if len(parts) > 1 else ""


def get_or_create_teacher(name, faculty, created_teachers):
    """Get or create teacher by name"""
    if not name or not name.strip():
        return None
        
    last_name, first_name = parse_teacher_name(name)
    if not last_name:
        return None
        
    # Generate a unique username
    username_base = f"{last_name.lower()}_{first_name.lower().replace('.', '').replace(' ', '_')}"
    username = username_base
    counter = 1
    
    # Ensure username is unique
    while CustomUser.objects.filter(username=username).exists():
        username = f"{username_base}_{counter}"
        counter += 1
    
    teacher_key = f"{last_name} {first_name}".strip()
    if teacher_key in created_teachers:
        return created_teachers[teacher_key]
    
    # Create new teacher
    teacher = CustomUser.objects.create(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=f"{username}@msu.portal",
        role='teacher',
        student_id=f"t{CustomUser.objects.filter(role='teacher').count() + 1:04d}",
        faculty=faculty or 'Не указан',
        course=0,
        is_staff=True,
        is_active=True
    )
    
    created_teachers[teacher_key] = teacher
    return teacher


class Command(BaseCommand):
    help = 'Import schedule from Google Sheets (one sheet per group)'

    def add_arguments(self, parser):
        parser.add_argument('--creds', type=str, required=True, 
                          help='Path to Google Service Account JSON key file')
        parser.add_argument('--sheet-id', type=str, required=True,
                          help='Google Sheet ID from the URL')
        parser.add_argument('--faculty', type=str, default='Не указан',
                          help='Faculty name for the groups')
        parser.add_argument('--course', type=int, default=1,
                          help='Course number for the groups')

    def handle(self, *args, **options):
        creds_path = options['creds']
        sheet_id = options['sheet_id']
        default_faculty = options['faculty']
        default_course = options['course']
        
        try:
            # Authenticate with Google Sheets API
            scope = ['https://spreadsheets.google.com/feeds', 
                    'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            client = gspread.authorize(creds)

            # Open the Google Sheet
            spreadsheet = client.open_by_key(sheet_id)
            
            # Process each worksheet (each group has its own worksheet)
            for worksheet in spreadsheet.worksheets():
                group_name = worksheet.title.strip()
                if not group_name:
                    continue
                    
                self.stdout.write(self.style.SUCCESS(f'\nProcessing group: {group_name}'))
                
                # Get or create group
                group, created = Group.objects.get_or_create(
                    name=group_name,
                    defaults={
                        'faculty': default_faculty,
                        'course': default_course
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created group: {group}'))
                
                # Get all records from the worksheet
                try:
                    records = worksheet.get_all_records()
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error reading worksheet {group_name}: {str(e)}'))
                    continue
                
                # Track created teachers and subjects
                created_teachers = {}
                created_subjects = {}
                now_day = "Понедельник"
                lesson_numb = 1
                with transaction.atomic():
                    for idx, row in enumerate(records, start=2):  # start=2 because of header row
                        try:
                            # Extract data from row
                            day = row.get('День недели', '').strip()
                            time = row.get('Время начала', '').strip()
                            subject_name = row.get('Название', '').strip()
                            first_teacher_name = row.get('Преподаватель', '').strip()
                            second_teacher_name = row.get('2-ой преподаватель', '').strip()
                            classroom = str(row.get('Кабинет', '')).strip()
                            another_classroom = str(row.get('Прочие кабинеты', '')).strip()
                            if now_day != day:
                                lesson_numb = 1
                                now_day = day
                            # Skip rows with missing required fields
                            if not all([day, time, subject_name]):
                                continue
                            # Initialize lesson counter for each day
                            if day not in getattr(self, 'day_lessons', {}):
                                if not hasattr(self, 'day_lessons'):
                                    self.day_lessons = {}
                                self.day_lessons[day] = 1
                            time_end = str(
                                    (datetime.strptime(time, '%H:%M') + timedelta(hours=1, minutes=35)).strftime('%H:%M'))
                            # Try to parse lesson number from time string (e.g., "1 пара: 09:00-10:30")
                            lesson_number = self.day_lessons[day]
                            lesson_match = re.search(r'^(\d+)\s*пара', time)
                            if lesson_match:
                                try:
                                    lesson_number = int(lesson_match.group(1))
                                except (ValueError, IndexError):
                                    pass
                            
                            # Increment counter for the next lesson of the day
                            self.day_lessons[day] = lesson_number + 1
                            
                            # Get or create teachers
                            teachers = []
                            for teacher_name in [first_teacher_name, second_teacher_name]:
                                if teacher_name:
                                    teacher = get_or_create_teacher(
                                        teacher_name, 
                                        default_faculty,
                                        created_teachers
                                    )
                                    if teacher:
                                        teachers.append(teacher)
                            if not teachers:
                                teachers = [get_or_create_teacher(
                                    "No Teacher",
                                    default_faculty,
                                    created_teachers
                                )]
                            
                            # Use the first teacher as the primary teacher for the subject
                            primary_teacher = teachers[0]
                            
                            # Create or get Subject with primary teacher
                            subject_key = f"{subject_name}_{primary_teacher.id}"
                            if subject_key not in created_subjects:
                                subject = Subject.objects.create(
                                    name=subject_name,
                                    teacher=primary_teacher
                                )
                                created_subjects[subject_key] = subject
                                self.stdout.write(self.style.SUCCESS(f'Created subject: {subject}'))
                            if subject_key in created_subjects:
                                subject = created_subjects[subject_key]

                                # Create or update Schedule
                                print(teachers, day, lesson_number)
                                if len(teachers) > 1:
                                    schedule, created = Schedule.objects.update_or_create(
                                        group=group,
                                        day=day,
                                        lesson_number=lesson_numb,
                                        defaults={
                                            'faculty': default_faculty,
                                            'time': time,
                                            'time_end': time_end,
                                            'subject': subject,
                                            'classroom': classroom,
                                            'another_classroom': another_classroom,
                                            'first_teacher_id': teachers[0].student_id,
                                            'first_teacher_name': teachers[0].last_name + ' ' + teachers[0].first_name,
                                            'second_teacher_id': teachers[1].student_id,
                                            'second_teacher_name': teachers[1].last_name + ' ' + teachers[1].first_name
                                        }
                                    )
                                else:
                                    schedule, created = Schedule.objects.update_or_create(
                                        group=group,
                                        day=day,
                                        lesson_number=lesson_numb,
                                        defaults={
                                            'faculty': default_faculty,
                                            'time': time,
                                            'time_end': time_end,
                                            'subject': subject,
                                            'classroom': classroom,
                                            'another_classroom': another_classroom,
                                            'first_teacher_id': teachers[0].student_id,
                                            'first_teacher_name': teachers[0].last_name + ' ' + teachers[0].first_name
                                        }
                                    )
                            lesson_numb += 1
                            if created:
                                self.stdout.write(self.style.SUCCESS(
                                    f'Created schedule: {group} - {day} - {time} - {subject_name}'))
                            
                        except Exception as e:
                            self.stderr.write(self.style.ERROR(
                                f'Error processing row {idx} in {group_name}: {str(e)}'))
                            continue

                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully processed group: {group_name}'))
            self.stdout.write(self.style.SUCCESS('\nImport completed successfully!'))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
            if hasattr(e, '__traceback__'):
                import traceback
                self.stderr.write(traceback.format_exc())
