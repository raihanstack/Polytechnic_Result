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
    technology_pattern = re.compile(r'Technology\s*:\s*(\d+)?\s*-?\s*(.+)')
    # Handles both ( ... ) and { ... }
    student_pattern = re.compile(r'(\d{6,7})\s*[({]([^)}]+)[)}]')
    
    # Extract the digit from semester string (e.g., '6th' -> '6')
    sem_digit = re.search(r'\d', semester)
    sem_digit = sem_digit.group() if sem_digit else None
    
    # Matches GPA values like gpa6: 3.50 or gpa6: ref
    gpa_pattern = re.compile(r'gpa(\d):\s*([0-4]\.\d{2}|ref)', re.IGNORECASE)
    # Matches 4-5 digit subject codes
    code_pattern = re.compile(r'\b(\d{4,5})\b')

    results_to_create = []
    
    current_inst_code = None
    current_inst_name = None
    current_tech_name = None

    # Use pypdfium2 for blazing fast C++ based text extraction instead of pdfplumber
    pdf = pdfium.PdfDocument(file_path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            
            if not text:
                continue
            
            # Find all institute, technology, and student matches on the entire page
            inst_matches = list(institute_pattern.finditer(text))
            tech_matches = list(technology_pattern.finditer(text))
            student_matches = list(student_pattern.finditer(text))
            
            # Sort them by their position in the text to maintain the State Machine order
            all_matches = sorted(inst_matches + tech_matches + student_matches, key=lambda m: m.start())
            
            for match in all_matches:
                # If this is an Institute match
                if match.re == institute_pattern:
                    current_inst_code = match.group(1).strip()
                    current_inst_name = match.group(2).strip()
                
                # If this is a Technology match
                elif match.re == technology_pattern:
                    current_tech_name = match.group(2).strip()
                
                # If this is a Student match
                else:
                    roll = match.group(1).strip()
                    content = match.group(2).strip()
                    
                    # 1. Extract GPA specific to the current semester
                    gpa = None
                    is_ref_in_current = False
                    
                    gpa_matches = gpa_pattern.findall(content)
                    for s_digit, val in gpa_matches:
                        if s_digit == sem_digit:
                            if val.lower() == 'ref':
                                is_ref_in_current = True
                            else:
                                gpa = val
                            break
                    
                    # 2. Extract all subject codes
                    failed_codes_list = code_pattern.findall(content)
                    
                    # 3. Apply Strict Drop Logic
                    current_sem_fails = 0
                    for code in failed_codes_list:
                        if code_to_sem.get(code) == semester:
                            current_sem_fails += 1
                    
                    # Determine Status
                    if current_sem_fails >= 4:
                        status = 'Semester Drop'
                        is_drop = True
                    elif current_sem_fails >= 1 or is_ref_in_current:
                        status = 'Referred'
                        is_drop = False
                    else:
                        status = 'Pass'
                        is_drop = False

                    failed_codes_str = ", ".join(failed_codes_list)

                    results_to_create.append(StudentResult(
                        roll=roll,
                        institute_code=current_inst_code,
                        institute_name=current_inst_name,
                        technology=current_tech_name,
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
