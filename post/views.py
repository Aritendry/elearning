from django.shortcuts import render , redirect
from post.models import Post , Domain

from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse

from bytez import Bytez
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login , logout


BYTEZ_KEY = "ed333e5f71baeb5a3f75b54b3db52102"
sdk = Bytez(BYTEZ_KEY)
model = sdk.model("Qwen/Qwen3-4B-Instruct-2507")

# Create your views here.

#Creation de la vue pour la pge d'accueil
def index(request):
    return render(request, 'index.html')

"""
Appelle l'API Bytez pour obtenir les scores AI et fake news
"""

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

""" Creation du CRUD post"""

@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        media = request.FILES.get("media")
        
        slug = slugify(title)
        base_slug = slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

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

        # génération des tags - CORRECTION ICI
        tags = generate_tags(content)
        for tag_name in tags:
            # récupère ou crée le Domain correspondant
            domain_obj, created = Domain.objects.get_or_create(name=tag_name)
            post.tags.add(domain_obj)  # <-- CHANGER domains en tags

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

def generate_tags(post_content):
    prompt = f"""
    Voici un texte :
    {post_content}

    Analyse ce texte et suggère 3 à 5 tags appropriés.
    Choisis parmi ces catégories : Science, Technology, Art, History,
    Sports, Education, Entertainment, Politics, Health, Environment, Business, Travel, Food, Culture, Gaming, Philosophy.
    
    Retourne uniquement une liste JSON comme : ["Tag1", "Tag2", "Tag3"]
    """
    
    try:
        output = model.run([{"role": "user", "content": prompt}])
        if output.output is None:
            raise ValueError("API ne répond pas")
        raw_content = output.output.get("content")
        
        # Nettoyer et parser
        clean_content = raw_content.strip()
        
        # Gérer différents formats de réponse
        if clean_content.startswith('[') and clean_content.endswith(']'):
            tags = json.loads(clean_content)
        elif '"' in clean_content:
            # Essaye de trouver les éléments entre guillemets
            import re
            tags = re.findall(r'"([^"]+)"', clean_content)
        else:
            # Séparer par virgules ou retours à la ligne
            tags = [tag.strip() for tag in clean_content.split(',') if tag.strip()]
        
        # Limiter à 5 tags max
        tags = tags[:5]
        
        # Valider les tags (optionnel)
        valid_categories = ["Science", "Technology", "Art", "History", "Sports", 
                          "Education", "Entertainment", "Politics", "Health", 
                          "Environment", "Business", "Travel", "Food", "Culture", 
                          "Gaming", "Philosophy"]
        
        # Nettoyer les tags
        cleaned_tags = []
        for tag in tags:
            # Capitaliser la première lettre
            tag = tag.strip().title()
            # Vérifier si le tag est valide (optionnel)
            if tag in valid_categories:
                cleaned_tags.append(tag)
            elif not valid_categories:  # Si on n'a pas de liste restreinte
                cleaned_tags.append(tag)
        
        if not cleaned_tags:
            cleaned_tags = ["General", "Education"]
            
        return cleaned_tags
        
    except Exception as e:
        print("Erreur dans generate_tags:", e)
        return ["General", "Education"]
    
PALIER_THEMES = {
    1: ["Bases du sujet", "Vocabulaire clé", "Concepts simples"],
    2: ["Concepts intermédiaires", "Exemples pratiques"],
    3: ["Applications concrètes", "Résolution de problèmes"],
    4: ["Études de cas", "Expérimentations"],
    5: ["Approfondissement", "Analyse critique"],
    6: ["Techniques avancées", "Optimisation"],
    7: ["Problèmes complexes", "Comparaisons"],
    8: ["Synthèse", "Interprétation"],
    9: ["Projets complets", "Intégration multi-concepts"],
    10:["Expertise avancée", "Défis et exercices complexes"]
}

def build_quiz_prompt(age, topic, palier, level):
    return f"""
Tu es un générateur de quiz éducatif.

Age: {age}
Sujet: {topic}
Palier: {palier}
Niveau: {level}

Retourne STRICTEMENT ce JSON (rien d'autre) :

{{
  "question": "...",
  "choices": ["...", "...", "...", "..."],
  "answer_index": 0
}}
"""

def call_quiz_ai(age, topic, palier, level):
    prompt = build_quiz_prompt(age, topic, palier, level)
    response = model.run([{"role": "user", "content": prompt}])

    print("Raw Bytez output:", response)  # log complet

    # Vérification sécurité
    if response.output is None or response.error:
        print("Erreur Bytez ou limite atteinte:", response.error)
        # fallback temporaire
        return {
            "question": f"Question {level} du palier {palier} (mock)",
            "choices": ["A", "B", "C", "D"],
            "answer_index": 0
        }

    raw_content = response.output.get("content")
    print("Content extrait:", raw_content)
    return json.loads(raw_content)

def build_quiz(age, topic):
    quiz = {"age": age, "topic": topic, "paliers": []}

    for palier in range(1, 11):
        palier_data = {"palier": palier, "levels": []}

        for level in range(1, 6):
            q = call_quiz_ai(age, topic, palier, level)
            q["level"] = level
            palier_data["levels"].append(q)

        quiz["paliers"].append(palier_data)

    return quiz

@csrf_exempt
def generate_quiz(request):
    palier = int(request.POST.get("palier", 0))  # 0 = question d’attente
    age = request.POST.get("age")
    topic = request.POST.get("topic")

    if not age or not topic:
        return JsonResponse({"error": "age or topic missing"}, status=400)

    if palier == 0:
        # Question de loading
        return JsonResponse({
            "palier": 0,
            "question": "Prépare-toi, le quiz commence bientôt !",
            "choices": ["Ok"],
            "answer_index": 0
        })
    else:
        # génération du palier demandé (1 à 10)
        questions = []
        for level in range(1, 6):
            q = call_quiz_ai(age, topic, palier, level)
            q["palier"] = palier
            q["level"] = level
            # Assurer qu'un thème est défini pour chaque question
            if "theme" not in q:
                q["theme"] = f"Thème du palier {palier}"
            questions.append(q)

        return JsonResponse({
            "palier": palier,
            "questions": questions
        })

def quiz_page(request):
    return render(request, "post/quiz.html")

"""
Creation du CRUD utilisateur
"""
def register_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if not username or not email or not password or not password2:
            messages.error(request, "Tous les champs sont requis.")
            return redirect("register_user")

        if password != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("register_user")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce pseudo est déjà utilisé.")
            return redirect("register_user")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect("register_user")
        # création de l'utilisateur
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Compte créé avec succès ! Tu peux maintenant te connecter.")
        return redirect("user_login")  # tu peux mettre la page de login ici

    return render(request, "post/register.html")    

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # <- ici tu passes bien l'utilisateur
            return redirect("index")  # page après login
        else:
            messages.error(request, "Identifiant ou mot de passe incorrect")
            return redirect("user_login")

    return render(request, "post/login.html")

def logout_user(request):
    logout(request)
    messages.success(request, "Tu es déconnecté.")
    return redirect("user_login")