from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .models import StudentResult, Subject

# Cache the results page for 15 minutes to handle high traffic
@cache_page(60 * 15)
def public_search_view(request):
    search_type = request.GET.get('search_type', 'individual')
    roll_query = request.GET.get('roll')
    inst_query = request.GET.get('institute_code')
    regulation_query = request.GET.get('regulation')
    
    results = None
    institute_results = None
    all_regulations = [choice[0] for choice in Subject.REGULATION_CHOICES]

    if regulation_query:
        if search_type == 'individual' and roll_query:
            results = StudentResult.objects.filter(roll=roll_query, regulation=regulation_query)
            for result in results:
                result.failed_subjects = result.get_failed_subjects_list()
                
        elif search_type == 'institute' and inst_query:
            # For institute, we fetch the latest results (e.g., aggregate or list)
            institute_results = StudentResult.objects.filter(institute_code=inst_query, regulation=regulation_query)

    context = {
        'search_type': search_type,
        'results': results,
        'institute_results': institute_results,
        'roll_query': roll_query,
        'inst_query': inst_query,
        'regulation_query': regulation_query,
        'all_regulations': all_regulations
    }
    return render(request, 'results/search.html', context)
