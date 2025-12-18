from django.db import models

class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True , blank=False , null=False)

    def __str__(self):
        return self.name

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
    tags = models.ManyToManyField(Domain , blank=True)
    likes = models.ManyToManyField('auth.User' , related_name='post_likes' , blank=True)
    dislikes = models.ManyToManyField('auth.User' , related_name='post_dislikes' , blank=True)

    @property
    def is_video(self):
        if not self.media:
            return False
        return self.media.name.lower().endswith(('.mp4', '.webm', '.mov'))
    
    def __str__(self):
        return f"Title : {self.title} , Author : {self.author.username} , Created at : {self.created_at}"
    

# models.py - Ajoute ces modèles après ton modèle Post

class UserPreference(models.Model):
    """Stocke les préférences des utilisateurs par tag"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    tag = models.ForeignKey(Domain, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)  # Score de préférence
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'tag']
    
    def __str__(self):
        return f"{self.user.username} - {self.tag.name}: {self.score}"

class PostRecommendation(models.Model):
    """Cache les recommandations personnalisées"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    recommended_posts = models.ManyToManyField(Post, related_name='recommendations')
    generated_at = models.DateTimeField(auto_now_add=True)
    cache_key = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return f"Recos for {self.user.username} at {self.generated_at}"
    