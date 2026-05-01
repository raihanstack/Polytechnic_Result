from django.shortcuts import render
from django.db.models import Avg, Q
from .models import StudentResult
import re

def parse_roll_input(roll_str):
    """
    Parses complex roll strings like '25841, 75272-78524, 79852.78525'
    Returns a set of unique roll numbers as strings.
    """
    if not roll_str:
        return set()
    
    # Normalize separators (replace dots, commas with spaces)
    normalized = re.sub(r'[.,]', ' ', roll_str)
    parts = normalized.split()
    
    final_rolls = set()
    for part in parts:
        if '-' in part:
            try:
                start, end = part.split('-')
                start_int = int(start.strip())
                end_int = int(end.strip())
                # Generate range (inclusive)
                for r in range(start_int, end_int + 1):
                    final_rolls.add(str(r))
            except (ValueError, TypeError):
                continue
        else:
            final_rolls.add(part.strip())
            
    return final_rolls

def public_search_view(request):
    search_type = request.GET.get('search_type', 'individual')
    roll_query = request.GET.get('roll', '').strip()
    regulation_query = request.GET.get('regulation', '2022')
    semester_query = request.GET.get('semester', '')
    institute_query = request.GET.get('institute', '').strip()
    
    results = None
    list_results = None
    stats = None

    if roll_query or (search_type == 'institute' and institute_query):
        base_query = StudentResult.objects.filter(regulation=regulation_query)
        if semester_query:
            base_query = base_query.filter(semester=semester_query)

        if search_type == 'individual' or (search_type == 'multi' and roll_query):
            rolls = parse_roll_input(roll_query)
            if len(rolls) == 1:
                results = base_query.filter(roll=list(rolls)[0])
                search_type = 'individual'
            elif len(rolls) > 1:
                list_results = base_query.filter(roll__in=rolls)
                search_type = 'multi'
        
        elif search_type == 'institute':
            list_results = base_query.filter(institute_code=institute_query)

        # Process List/Dashboard Results
        if list_results is not None:
            list_results = list_results.order_by('-gpa', 'roll')
            total_count = list_results.count()
            
            if total_count > 0:
                passed_qs = list_results.filter(status='Pass')
                referred_qs = list_results.filter(status='Referred')
                dropped_qs = list_results.filter(status='Semester Drop')
                
                passed_count = passed_qs.count()
                failed_count = referred_qs.count() + dropped_qs.count()
                pass_percentage = round((passed_count / total_count) * 100, 1)
                
                avg_gpa = list_results.filter(gpa__gt=0).aggregate(Avg('gpa'))['gpa__avg']
                avg_gpa = round(avg_gpa, 2) if avg_gpa else 0.00

                top_student = list_results.filter(gpa__gt=0).order_by('-gpa').first()
                top_roll = top_student.roll if top_student else "N/A"

                stats = {
                    'total': total_count,
                    'passed': passed_count,
                    'failed': failed_count,
                    'pass_percentage': pass_percentage,
                    'passed_percent': pass_percentage,
                    'avg_gpa': avg_gpa,
                    'top_roll': top_roll,
                    'groups': []
                }

                # Grouping for UI
                final_groups = []
                if passed_qs.exists():
                    final_groups.append({'name': 'Passed', 'color': 'emerald', 'students': passed_qs})
                if referred_qs.exists():
                    final_groups.append({'name': 'Referred', 'color': 'amber', 'students': referred_qs})
                if dropped_qs.exists():
                    final_groups.append({'name': 'Semester Drop', 'color': 'red', 'students': dropped_qs})
                
                stats['groups'] = final_groups

    context = {
        'search_type': search_type,
        'results': results,
        'list_results': list_results,
        'stats': stats,
        'roll_query': roll_query,
        'regulation_query': regulation_query,
        'semester_query': semester_query,
        'institute_query': institute_query,
    }
    
    return render(request, 'results/search.html', context)
