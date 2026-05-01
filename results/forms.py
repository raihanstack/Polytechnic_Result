from django import forms
from .models import Subject

class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(label="BTEB Result PDF", help_text="Upload the official PDF result sheet.")
    semester = forms.CharField(max_length=50, label="Semester", help_text="e.g., 1st, 2nd, 3rd")
    regulation = forms.ChoiceField(choices=Subject.REGULATION_CHOICES, label="Regulation")
