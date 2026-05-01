import re
import pypdfium2 as pdfium
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

    # Use pypdfium2 for blazing fast C++ based text extraction instead of pdfplumber
    pdf = pdfium.PdfDocument(file_path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            
            if not text:
                continue
            
            # Find all institute headers and student blocks on the entire page
            inst_matches = list(institute_pattern.finditer(text))
            student_matches = list(student_pattern.finditer(text))
            
            # Sort them by their position in the text to maintain the State Machine order
            all_matches = sorted(inst_matches + student_matches, key=lambda m: m.start())
            
            for match in all_matches:
                # If this is an Institute match
                if match.re == institute_pattern:
                    current_inst_code = match.group(1).strip()
                    current_inst_name = match.group(2).strip()
                
                # If this is a Student match
                else:
                    roll = match.group(1).strip()
                    content = match.group(2).strip()
                    
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
    finally:
        pdf.close()

    # Bulk insert for massive speed optimization
    with transaction.atomic():
        StudentResult.objects.bulk_create(results_to_create, ignore_conflicts=True)

    return len(results_to_create)
