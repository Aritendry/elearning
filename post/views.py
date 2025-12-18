from django.shortcuts import render , redirect
from post.models import Post

from django.utils.text import slugify
from django.contrib.auth.decorators import login_required

# Create your views here.

#Creation de la vue pour la pge d'accueil
def index(request):
    return render(request, 'index.html')

def get_ai_fake_score(text):
    prompt = (
        "Analyse ce texte et renvoie uniquement deux chiffres séparés par un point-virgule : "
        "le premier chiffre (0-100) correspond à la probabilité que le texte soit écrit par une IA, "
        "le deuxième chiffre (0-100) correspond à la probabilité que le texte soit une fake news. "
        "Ne renvoie rien d'autre que chiffre;chiffre. "
        f"Texte : '''{text}'''"
    )

    output = model.run([{"role": "user", "content": prompt}])

    # Affiche tout ce que l'API renvoie
    print("Raw output from Bytez:", output)

    # Récupère le texte renvoyé
    try:
        result_text = output.output['content']
        print("Parsed result_text:", result_text)
        ia_score, fake_score = map(float, result_text.split(";"))
    except Exception as e:
        print("Erreur parsing API:", e)
        ia_score, fake_score = None, None

    return ia_score, fake_score

@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        media = request.FILES.get("media")
        
        # Slug automatique
        slug = slugify(title)
        base_slug = slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # 🔹 Ici on récupère les scores AI et fake
        ia_score, fake_score = get_ai_fake_score(content)

        post = Post(
            title=title,
            content=content,
            media=media,
            slug=slug,
            author=request.user,
            made_ai=ia_score,
            fake_news=fake_score
        )
        post.save()
        return redirect('index')

    return render(request, "post/form_post.html")
   

def all_post(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'post/all_post.html', context={'posts': posts})

def detail_post(request, slug):
    post = Post.objects.get(slug=slug)
    return render(request, 'post/detail_post.html', context={'post': post})

def view_api_response(request):
    return render(request, 'post/test_api.html')

from bytez import Bytez

BYTEZ_KEY = "ed333e5f71baeb5a3f75b54b3db52102"
sdk = Bytez(BYTEZ_KEY)
model = sdk.model("Qwen/Qwen3-4B-Instruct-2507")

