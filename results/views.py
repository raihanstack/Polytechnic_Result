from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .models import StudentResult, Subject

# Cache the results page for 15 minutes to handle high traffic
@cache_page(60 * 15)
def public_search_view(request):
    roll_query = request.GET.get('roll')
    regulation_query = request.GET.get('regulation')
    
    results = None
    # We provide static regulation choices based on the Subject model
    all_regulations = [choice[0] for choice in Subject.REGULATION_CHOICES]

    if roll_query and regulation_query:
        # Order by semester is already defined in the model's Meta class
        results = StudentResult.objects.filter(roll=roll_query, regulation=regulation_query)

        # Enhance results with Subject objects for failed codes
        for result in results:
            result.failed_subjects = result.get_failed_subjects_list()

    context = {
        'results': results,
        'roll_query': roll_query,
        'regulation_query': regulation_query,
        'all_regulations': all_regulations
    }
    return render(request, 'results/search.html', context)
