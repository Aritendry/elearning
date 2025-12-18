from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class Post(models.Model):
    title = models.CharField(max_length=100 , blank=False , null=False)
    content = models.TextField(max_length=600,blank=False , null=False)
    made_ai = models.FloatField(blank=True , null=True)
    fake_news = models.FloatField(blank=True , null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    media = models.FileField(upload_to='media/' , blank=True , null=True)
    slug = models.SlugField(max_length=150 , unique=True , blank=False , null=False)
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)


    @property
    def is_video(self):
        if not self.media:
            return False
        return self.media.name.lower().endswith(('.mp4', '.webm', '.mov'))
    
    def __str__(self):
        return f"Title : {self.title} , Author : {self.author.username} , Created at : {self.created_at}"
    
class User(AbstractUser):
    pseudo = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    moyenne_ia = models.FloatField(default=0.0)  # moyenne % IA sur ses posts

    # followers et followings
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)

    def __str__(self):
        return self.pseudo

    def update_moyenne_ia(self):
        # calcule la moyenne des pourcentages IA sur ses posts
        posts = self.posts.all()  # suppose qu'il y a un modèle Post avec ForeignKey vers User
        if posts.exists():
            self.moyenne_ia = sum(p.ia_score for p in posts) / posts.count()
            self.save()