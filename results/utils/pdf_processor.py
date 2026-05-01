import re
import pdfplumber
from django.db import transaction
from results.models import Subject, StudentResult

def parse_and_process_pdf(file_path, semester, regulation):
    """
    Parses a BTEB result PDF acting as a State Machine.
    Extracts Institute Code/Name and accurately parses curly brace blocks { ... }.
    """
    # Pre-fetch subjects to accurately enforce the Drop Rule for the CURRENT semester
    subjects = Subject.objects.filter(regulation=regulation)
    code_to_sem = {sub.subject_code: sub.semester for sub in subjects}

    institute_pattern = re.compile(r'(\d{5})\s*-\s*(.+)')
    student_pattern = re.compile(r'(\d{6})\s*\{([^}]+)\}')
    # Matches GPA values like 3.50, 4.00
    gpa_pattern = re.compile(r'gpa\d:\s*([0-4]\.\d{2})')
    # Matches 4-5 digit subject codes, ignoring the (T)/(P) suffix
    code_pattern = re.compile(r'\b(\d{4,5})\b')

    results_to_create = []
    
    current_inst_code = None
    current_inst_name = None

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            for line in lines:
                # 1. Check for Institute Header
                inst_match = institute_pattern.search(line)
                if inst_match:
                    current_inst_code = inst_match.group(1).strip()
                    current_inst_name = inst_match.group(2).strip()

                # 2. Check for Student Results in this line
                # Note: finditer is used in case multiple students are on one line
                for student_match in student_pattern.finditer(line):
                    roll = student_match.group(1).strip()
                    content = student_match.group(2).strip()
                    
                    # Extract GPA if present
                    gpa_match = gpa_pattern.search(content)
                    gpa = gpa_match.group(1) if gpa_match else None
                    
                    # Extract all failed subject codes (excluding the roll number itself which isn't in the {} block anyway)
                    failed_codes_list = code_pattern.findall(content)
                    
                    # 3. Apply Strict Drop Logic
                    # Count how many of these failed codes actually belong to the uploaded semester
                    current_sem_fails = 0
                    for code in failed_codes_list:
                        if code_to_sem.get(code) == semester:
                            current_sem_fails += 1
                    
                    if len(failed_codes_list) == 0 and gpa:
                        status = 'Pass'
                        is_drop = False
                    elif current_sem_fails >= 4:
                        status = 'Semester Drop'
                        is_drop = True
                    else:
                        status = 'Referred'
                        is_drop = False

                    failed_codes_str = ", ".join(failed_codes_list)

                    results_to_create.append(StudentResult(
                        roll=roll,
                        institute_code=current_inst_code,
                        institute_name=current_inst_name,
                        semester=semester,
                        regulation=regulation,
                        gpa=gpa,
                        failed_subject_codes=failed_codes_str,
                        status=status,
                        is_drop=is_drop,
                    ))

    # Bulk insert for massive speed optimization
    with transaction.atomic():
        StudentResult.objects.bulk_create(results_to_create, ignore_conflicts=True)

    return len(results_to_create)
