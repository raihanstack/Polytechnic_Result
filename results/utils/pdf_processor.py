import re
import pdfplumber
from django.db import transaction
from results.models import Subject, StudentResult

def parse_and_process_pdf(file_path, semester, regulation):
    """
    Parses a BTEB result PDF and updates the database.
    Assumes standard format: 'Roll (GPA)' for passed or 'Roll (Code1, Code2)' for failures.
    """
    # Regex to capture roll number and the content inside the parentheses.
    # E.g., 123456 (3.45) OR 123456 (25911, 25912)
    pattern = re.compile(r'(\d{6})\s*\(([^)]+)\)')

    results_to_create_or_update = []
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            matches = pattern.findall(text)
            for roll, content in matches:
                # Determine if content is a GPA or a list of failed subjects
                is_passed = False
                gpa = None
                failed_codes_str = ""
                failed_codes_list = []
                
                content_clean = content.strip()
                # Check if it's a GPA (e.g., 3.50 or 4.00)
                if re.match(r'^[0-4]\.\d{2}$', content_clean):
                    is_passed = True
                    gpa = content_clean
                else:
                    # It's a list of failed subjects
                    # Extract just the codes (5 digit numbers typically)
                    code_pattern = re.compile(r'\d{4,5}')
                    failed_codes_list = code_pattern.findall(content_clean)
                    failed_codes_str = ", ".join(failed_codes_list)
                
                # Apply Logic
                if is_passed or len(failed_codes_list) == 0:
                    status = 'Pass'
                    is_drop = False
                elif len(failed_codes_list) >= 4:
                    status = 'Semester Drop'
                    is_drop = True
                else:
                    status = 'Referred'
                    is_drop = False

                results_to_create_or_update.append({
                    'roll': roll,
                    'semester': semester,
                    'regulation': regulation,
                    'gpa': gpa,
                    'failed_subject_codes': failed_codes_str,
                    'status': status,
                    'is_drop': is_drop,
                })

    # Bulk insert or update
    with transaction.atomic():
        for res in results_to_create_or_update:
            StudentResult.objects.update_or_create(
                roll=res['roll'],
                semester=res['semester'],
                defaults={
                    'regulation': res['regulation'],
                    'gpa': res['gpa'],
                    'failed_subject_codes': res['failed_subject_codes'],
                    'status': res['status'],
                    'is_drop': res['is_drop']
                }
            )

    return len(results_to_create_or_update)
