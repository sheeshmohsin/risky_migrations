from django.urls import path
from . import views

urlpatterns = [
    path('list_large/', views.list_large, name='list_large'),
    path('update_order/', views.update_order, name='update_order'),
]
