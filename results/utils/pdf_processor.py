import re
import pdfplumber
from django.db import transaction
from results.models import Subject, StudentResult

def parse_and_process_pdf(file_path, semester, regulation):
    """
    Parses a BTEB result PDF and updates the database.
    Assumes standard format: 'Roll (GPA)' for passed or 'Roll (Code1, Code2)' for failures.
    """
    # Using the optimized regex requested to capture digits, spaces, commas, and dots (for GPA)
    pattern = re.compile(r'(\d{6})\s*\(([\d\s,.]*)\)')

    results_to_create = []
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            matches = pattern.findall(text)
            for roll, content in matches:
                is_passed = False
                gpa = None
                failed_codes_str = ""
                failed_codes_list = []
                
                content_clean = content.strip()
                if re.match(r'^[0-4]\.\d{2}$', content_clean):
                    is_passed = True
                    gpa = content_clean
                else:
                    code_pattern = re.compile(r'\d{4,5}')
                    failed_codes_list = code_pattern.findall(content_clean)
                    failed_codes_str = ", ".join(failed_codes_list)
                
                if is_passed or len(failed_codes_list) == 0:
                    status = 'Pass'
                    is_drop = False
                elif len(failed_codes_list) >= 4:
                    status = 'Semester Drop'
                    is_drop = True
                else:
                    status = 'Referred'
                    is_drop = False

                results_to_create.append(StudentResult(
                    roll=roll,
                    semester=semester,
                    regulation=regulation,
                    gpa=gpa,
                    failed_subject_codes=failed_codes_str,
                    status=status,
                    is_drop=is_drop,
                ))

    # Bulk insert for speed optimization
    with transaction.atomic():
        # Using ignore_conflicts=True so it silently ignores duplicates during bulk creation
        StudentResult.objects.bulk_create(results_to_create, ignore_conflicts=True)

    return len(results_to_create)
