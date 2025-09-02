# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name='home'),
    path("", views.callback, name="callback"),  # capture code at root
    path("connect/", views.connect, name="connect"),
    path("update-random/", views.update_random, name="update_random"),
    path('status/', views.status, name='status'),
    path('logout/', views.logout, name='logout'),
    
]