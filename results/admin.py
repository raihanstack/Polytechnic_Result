from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.conf import settings
import os
from import_export.admin import ImportExportModelAdmin
from .models import Subject, StudentResult
from .forms import PDFUploadForm
from .utils.pdf_processor import parse_and_process_pdf
from .utils.subject_processor import parse_course_structure_pdf

@admin.register(Subject)
class SubjectAdmin(ImportExportModelAdmin):
    change_list_template = "admin/results/subject/change_list.html"
    list_display = ('subject_code', 'subject_name', 'semester', 'regulation', 'technology')
    list_filter = ('regulation', 'semester', 'technology')
    search_fields = ('subject_code', 'subject_name', 'technology')
    ordering = ('regulation', 'semester', 'subject_code')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-structure/', self.admin_site.admin_view(self.upload_structure_view), name='subject_upload_structure'),
        ]
        return custom_urls + urls

    def upload_structure_view(self, request):
        if request.method == 'POST':
            pdf_file = request.FILES.get('pdf_file')
            if pdf_file:
                temp_path = os.path.join(settings.BASE_DIR, 'temp_structure_upload.pdf')
                with open(temp_path, 'wb+') as destination:
                    for chunk in pdf_file.chunks():
                        destination.write(chunk)
                
                try:
                    num_processed = parse_course_structure_pdf(temp_path)
                    self.message_user(request, f"Successfully imported {num_processed} subjects from Course Structure.", messages.SUCCESS)
                except Exception as e:
                    self.message_user(request, f"Error: {str(e)}", messages.ERROR)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                return redirect('..')
        
        context = dict(
            self.admin_site.each_context(request),
            title="Upload Course Structure PDF",
            opts=self.model._meta,
        )
        return render(request, 'admin/results/subject/upload_structure.html', context)

@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    change_list_template = "admin/results/studentresult/change_list.html"
    list_display = ('roll', 'semester', 'regulation', 'status', 'is_drop', 'gpa')
    search_fields = ('roll', 'failed_subject_codes')
    list_filter = ('status', 'is_drop', 'semester', 'regulation')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-pdf/', self.admin_site.admin_view(self.upload_pdf_view), name='results_studentresult_upload_pdf'),
        ]
        return custom_urls + urls

    def upload_pdf_view(self, request):
        if request.method == 'POST':
            form = PDFUploadForm(request.POST, request.FILES)
            if form.is_valid():
                pdf_file = request.FILES['pdf_file']
                semester = form.cleaned_data['semester']
                regulation = form.cleaned_data['regulation']
                
                temp_path = os.path.join(settings.BASE_DIR, 'temp_admin_upload.pdf')
                with open(temp_path, 'wb+') as destination:
                    for chunk in pdf_file.chunks():
                        destination.write(chunk)
                
                try:
                    num_processed = parse_and_process_pdf(temp_path, semester, regulation)
                    self.message_user(request, f"Successfully processed {num_processed} student results for {semester} semester ({regulation} regulation).", messages.SUCCESS)
                    cache.clear()
                except Exception as e:
                    self.message_user(request, f"An error occurred: {str(e)}", messages.ERROR)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                return redirect('..')
        else:
            form = PDFUploadForm()

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            opts=self.model._meta,
            title="Bulk Upload PDF Results",
        )
        return render(request, "admin/results/studentresult/upload_pdf.html", context)
