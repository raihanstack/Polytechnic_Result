from django import forms
from .models import Subject

class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(label="BTEB Result PDF", help_text="Upload the official PDF result sheet.")
    semester = forms.ChoiceField(choices=Subject.SEMESTER_CHOICES, label="Semester")
    regulation = forms.ChoiceField(choices=Subject.REGULATION_CHOICES, label="Regulation")
