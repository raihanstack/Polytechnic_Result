from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .models import StudentResult, Subject

# Cache the results page for 15 minutes to handle high traffic
@cache_page(60 * 15)
def public_search_view(request):
    search_type = request.GET.get('search_type', 'individual')
    roll_query = request.GET.get('roll')
    inst_query = request.GET.get('institute_code')
    tech_query = request.GET.get('technology')
    regulation_query = request.GET.get('regulation')
    semester_query = request.GET.get('semester')
    
    results = None
    list_results = None
    stats = None
    all_regulations = [choice[0] for choice in Subject.REGULATION_CHOICES]
    all_semesters = [choice[0] for choice in Subject.SEMESTER_CHOICES]
    all_technologies = StudentResult.objects.values_list('technology', flat=True).distinct().exclude(technology__isnull=True)

    if regulation_query:
        if search_type == 'individual' and roll_query:
            results = StudentResult.objects.filter(roll=roll_query, regulation=regulation_query)
            for result in results:
                result.failed_subjects = result.get_failed_subjects_list()
                
        elif search_type == 'institute' and inst_query:
            base_query = StudentResult.objects.filter(institute_code=inst_query, regulation=regulation_query)
            if semester_query:
                list_results = base_query.filter(semester=semester_query)
                stats = {
                    'total': list_results.count(),
                    'passed': list_results.filter(status='Pass').count(),
                    'referred': list_results.filter(status='Referred').count(),
                    'dropped': list_results.filter(status='Semester Drop').count(),
                }
            else:
                list_results = base_query

        elif search_type == 'group' and tech_query:
            base_query = StudentResult.objects.filter(technology=tech_query, regulation=regulation_query)
            if semester_query:
                list_results = base_query.filter(semester=semester_query)
                stats = {
                    'total': list_results.count(),
                    'passed': list_results.filter(status='Pass').count(),
                    'referred': list_results.filter(status='Referred').count(),
                    'dropped': list_results.filter(status='Semester Drop').count(),
                }
            else:
                list_results = base_query

    context = {
        'search_type': search_type,
        'results': results,
        'list_results': list_results,
        'stats': stats,
        'roll_query': roll_query,
        'inst_query': inst_query,
        'tech_query': tech_query,
        'regulation_query': regulation_query,
        'semester_query': semester_query,
        'all_regulations': all_regulations,
        'all_semesters': all_semesters,
        'all_technologies': all_technologies
    }
    return render(request, 'results/search.html', context)
