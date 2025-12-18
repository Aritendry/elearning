from django.contrib import admin
from .models import Post , UserPreference , PostRecommendation
# Register your models here.

admin.site.register(Post)
admin.site.register(UserPreference)
admin.site.register(PostRecommendation)