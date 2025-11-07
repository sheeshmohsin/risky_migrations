from django.urls import path
from . import views

urlpatterns = [
    path('list_large/', views.list_large, name='list_large'),
]
