from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .models import StudentResult, Subject

# Cache the results page for 15 minutes to handle high traffic
@cache_page(60 * 15)
def public_search_view(request):
    roll_query = request.GET.get('roll')
    semester_query = request.GET.get('semester')
    
    results = None
    all_semesters = StudentResult.objects.values_list('semester', flat=True).distinct()

    if roll_query:
        results = StudentResult.objects.filter(roll=roll_query)
        
        if semester_query and semester_query != 'All':
            results = results.filter(semester=semester_query)

        # Enhance results with Subject objects for failed codes
        for result in results:
            result.failed_subjects = result.get_failed_subjects_list()

    context = {
        'results': results,
        'roll_query': roll_query,
        'semester_query': semester_query,
        'all_semesters': all_semesters
    }
    return render(request, 'results/search.html', context)
