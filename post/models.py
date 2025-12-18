from django.db import models

# Create your models here.
class Post(models.Model):
    title = models.CharField(max_length=100 , blank=False , null=False)
    content = models.TextField(max_length=600,blank=False , null=False)
    made_ai = models.FloatField(blank=True , null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    media = models.FileField(upload_to='media/' , blank=True , null=True)
    slug = models.SlugField(max_length=150 , unique=True , blank=False , null=False)
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    def __str__(self):
        return f"Title : {self.title} , Author : {self.author.username} , Created at : {self.created_at}"