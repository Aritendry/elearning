from django.contrib import admin
from django.urls import path
from post.views import index, create_post, all_post, detail_post, view_api_response, quiz_page, generate_quiz, register_user, user_login, logout_user, toggle_like, toggle_dislike, user_profile, update_post, delete_post, post_form

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    
    # Routes de posts - ORDRE IMPORTANT !
    path('posts/', all_post, name='all_post'),  # Liste des posts
    path('post/create/', post_form, name='create_post'),  # Création
    path('post/<slug:slug>/', detail_post, name='detail_post'),  # Détail
    path('post/<slug:slug>/edit/', post_form, name='update_post'),  # Modification
    path('post/<slug:slug>/delete/', delete_post, name='delete_post'),  # Suppression
    
    # Routes de likes/dislikes
    path('post/<int:post_id>/like/', toggle_like, name='toggle_like'),
    path('post/<int:post_id>/dislike/', toggle_dislike, name='toggle_dislike'),
    
    # Authentification
    path('register/', register_user, name='register_user'),
    path('login/', user_login, name='user_login'),
    path('logout/', logout_user, name='logout_user'),
    
    # Profil
    path('profile/<str:username>/', user_profile, name='user_profile'),
    
    # Quiz
    path('quiz/', quiz_page, name='quiz_page'),
    path('quiz/generate/', generate_quiz, name='generate_quiz'),
    
    # API test
    path('test_api/', view_api_response, name='test_api'),
]

# SUPPRIMEZ l'ancienne route 'create_post/' si vous utilisez 'post_form'
# SUPPRIMEZ aussi 'all_post/' si vous utilisez 'posts/'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)