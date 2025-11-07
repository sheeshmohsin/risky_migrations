from django.urls import path
from . import views

urlpatterns = [
    path('list_large/', views.list_large, name='list_large'),
    path('search_by_legacy_code/', views.search_by_legacy_code, name='search_by_legacy_code'),
]
