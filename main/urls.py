from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', views.profile, name='profile'),

    # Новости
    path('news/add/', views.add_news, name='add_news'),
    path('news/edit/<int:news_id>/', views.edit_news, name='edit_news'),
    path('download/<int:news_id>/', views.download_news, name='download_news'),
    path('news/delete/<int:news_id>/', views.delete_news, name='delete_news'),
]