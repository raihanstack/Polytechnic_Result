from django.urls import path
from . import views

urlpatterns = [
    path('', views.public_search_view, name='public_search'),
]
