from django.db import models

class Subject(models.Model):
    REGULATION_CHOICES = (
        ('2010', '2010'),
        ('2016', '2016'),
        ('2022', '2022'),
    )
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=255)
    semester = models.CharField(max_length=50)
    regulation = models.CharField(max_length=10, choices=REGULATION_CHOICES)
    technology = models.CharField(max_length=100)

    class Meta:
        unique_together = ('subject_code', 'regulation')

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"


class StudentResult(models.Model):
    STATUS_CHOICES = (
        ('Pass', 'Pass'),
        ('Referred', 'Referred'),
        ('Semester Drop', 'Semester Drop'),
    )
    
    roll = models.CharField(max_length=20, db_index=True)
    reg_no = models.CharField(max_length=20, blank=True, null=True)
    semester = models.CharField(max_length=50)
    regulation = models.CharField(max_length=10)
    gpa = models.CharField(max_length=10, blank=True, null=True)
    failed_subject_codes = models.TextField(blank=True, null=True, help_text="Comma separated codes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_drop = models.BooleanField(default=False)

    class Meta:
        unique_together = ('roll', 'semester')
        ordering = ['semester']

    def __str__(self):
        return f"{self.roll} - {self.semester} ({self.status})"

    def get_failed_subjects_list(self):
        if not self.failed_subject_codes:
            return []
        codes = [code.strip() for code in self.failed_subject_codes.split(',') if code.strip()]
        return Subject.objects.filter(subject_code__in=codes, regulation=self.regulation)
