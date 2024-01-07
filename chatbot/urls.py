from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dialogs/', views.dialogs, name='dialogs'),
    path('new_chat/', views.new_chat, name='new_chat'),
    path('save_chat/', views.save_chat, name='save_chat'),
    path('del_chat/', views.del_chat, name='del_chat'),
    path('gen_json/', views.gen_json, name='gen_json'),
    path('error-handler/', views.error_handler, name='error_handler'),
    path('accounts/', include('django.contrib.auth.urls')),
]