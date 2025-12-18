from django.shortcuts import render , redirect
from models import Post

from django.utils.text import slugify
from django.contrib.auth.decorators import login_required

# Create your views here.

#Creation de la vue pour la pge d'accueil
def index(request):
    return render(request, 'index.html')

@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        media = request.FILES.get("media")
        
        # Slug automatique (à partir du titre)
        slug = slugify(title)
        
        # Si slug existe déjà, on ajoute un chiffre
        base_slug = slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = Post(
            title=title,
            content=content,
            media=media,
            slug=slug,
            author=request.user
        )
        post.save()

        return redirect("post_detail", slug=post.slug)

    return render(request, "form_post.html")    