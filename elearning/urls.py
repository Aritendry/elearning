"""
URL configuration for elearning project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from post.views import index , create_post , all_post ,detail_post ,view_api_response , quiz_page , generate_quiz , register_user , user_login , logout_user

# Permettre à Django de lire les fichiers média en mode développement
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('create_post/', create_post, name='create_post'),
    path('all_post/', all_post, name='all_post'),
    path('post/<slug:slug>/', detail_post, name='detail_post'),
    path('test_api/', view_api_response, name='test_api'),
    path('quiz/', quiz_page, name='quiz_page'),
    path('quiz/generate/', generate_quiz, name='generate_quiz'),
    path('register/', register_user, name='register_user'),
    path('login/' , user_login, name='user_login'),
    path('logout/' , logout_user, name='logout_user'),


]

# Configuration pour servir les fichiers média en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
