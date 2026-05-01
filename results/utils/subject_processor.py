import re
import pypdfium2 as pdfium
from django.db import transaction
from results.models import Subject

def parse_course_structure_pdf(file_path):
    """
    Parses a BTEB Course Structure PDF to extract Subjects.
    """
    tech_pattern = re.compile(r'Name of Technology\s*:\s*(.+)', re.IGNORECASE)
    reg_pattern = re.compile(r'Probidhan-(\d{4})', re.IGNORECASE)
    sem_pattern = re.compile(r'(\d(?:st|nd|rd|th))\s+Semester', re.IGNORECASE)
    # Pattern for Sl No, Subject Code, and Subject Name
    # E.g. "1 21011 Engineering Drawing"
    subject_row_pattern = re.compile(r'^\s*(\d+)\s+(\d{4,6})\s+(.+)$', re.MULTILINE)

    subjects_to_create = []
    
    current_tech = "Unknown"
    current_reg = "2022"
    current_sem = "1st"

    pdf = pdfium.PdfDocument(file_path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            
            if not text:
                continue

            # Extract Global Info from page if present
            tech_match = tech_pattern.search(text)
            if tech_match:
                current_tech = tech_match.group(1).split('(')[0].strip()
            
            reg_match = reg_pattern.search(text)
            if reg_match:
                current_reg = reg_match.group(1).strip()

            # Split into lines to find Semester headers and Subject rows
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                
                # Check for Semester header
                sem_match = sem_pattern.search(line)
                if sem_match:
                    current_sem = sem_match.group(1).strip()
                
                # Check for Subject row
                sub_match = subject_row_pattern.match(line)
                if sub_match:
                    # Clean up the name - sometimes extra columns might be captured if they follow the name
                    # But usually Sl No and Code are distinct enough.
                    sl_no = sub_match.group(1)
                    code = sub_match.group(2)
                    name_raw = sub_match.group(3).strip()
                    
                    # Name might contain trailing numbers from periods/credits, so we clean it
                    # Usually the name is followed by a tab or multiple spaces in a well-formatted PDF
                    # or it's followed by a number like '2' or '3'.
                    # Let's take the string part before any major space+digit combo if needed, 
                    # but for now we'll take the whole match and trim.
                    name = re.split(r'\s{2,}', name_raw)[0].strip()
                    
                    subjects_to_create.append(Subject(
                        subject_code=code,
                        subject_name=name,
                        semester=current_sem,
                        regulation=current_reg,
                        technology=current_tech
                    ))
    finally:
        pdf.close()

    # Bulk insert with conflict ignore
    with transaction.atomic():
        Subject.objects.bulk_create(subjects_to_create, ignore_conflicts=True)

    return len(subjects_to_create)
