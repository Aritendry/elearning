from django.shortcuts import render , redirect
from post.models import Post ,  Domain , UserPreference , PostRecommendation

from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse

from bytez import Bytez
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login , logout

from django.core.cache import cache
import hashlib

import numpy as np
from django.db.models import Count, Q
from collections import defaultdict
from django.utils import timezone

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
# views.py - Modifie la vue all_post existante

def all_post(request):
    """Affiche les posts avec recommandations personnalisées"""
    if request.user.is_authenticated:
        # Récupérer les posts recommandés pour l'utilisateur
        recommended_posts = recommendation_engine.get_personalized_recommendations(request.user, limit=10)
        
        # Récupérer les IDs des posts recommandés pour éviter les doublons
        recommended_ids = [post.id for post in recommended_posts]
        
        # Récupérer d'autres posts récents (excluant ceux déjà recommandés)
        other_posts = Post.objects.exclude(id__in=recommended_ids).order_by('-created_at')[:10]
        
        # Combiner : d'abord les recommandés, puis les autres
        posts = list(recommended_posts) + list(other_posts)
        
        # Indiquer quels posts sont recommandés pour le template
        recommended_post_ids = set(recommended_ids)
    else:
        # Pour utilisateurs non connectés : posts populaires
        posts = recommendation_engine.get_popular_posts(limit=20)
        recommended_post_ids = set()
    
    return render(request, 'post/all_post.html', {
        'posts': posts,
        'recommended_post_ids': recommended_post_ids
    })

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
    10: ["Expertise avancée", "Défis et exercices complexes"]
}

class QuizGenerator:
    """Classe optimisée pour la génération de quiz avec cache et batch processing"""
    
    def __init__(self, model):
        self.model = model
        self.cache_timeout = 3600  # 1 heure en cache
        
    def _get_cache_key(self, age, topic, palier):
        """Génère une clé de cache unique pour le quiz"""
        key_str = f"quiz_{age}_{topic}_{palier}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _build_complete_prompt(self, age, topic, palier):
        """Construit le prompt pour générer les 5 questions d'un palier en une requête"""
        themes = PALIER_THEMES.get(palier, ["Concepts généraux"])
        
        return f"""
Tu es un générateur de quiz éducatif intelligent. Crée 5 questions progressives pour un élève de {age} ans.

CONTEXTE:
- Sujet: {topic}
- Palier {palier} (thèmes: {', '.join(themes)})
- Difficulté: progressive du niveau 1 (facile) au niveau 5 (difficile)

INSTRUCTIONS:
1. Question 1 (niveau 1): Très simple, vérifie la compréhension des bases
2. Question 2 (niveau 2): Introduit des concepts intermédiaires
3. Question 3 (niveau 3): Application pratique des concepts
4. Question 4 (niveau 4): Analyse ou étude de cas
5. Question 5 (niveau 5): Le plus difficile, teste la maîtrise approfondie

EXIGENCES:
- Chaque question doit être claire et concise
- Les choix doivent être plausibles (éviter les indices évidents)
- La bonne réponse doit être justifiée

FORMAT DE RÉPONSE:
Retourne STRICTEMENT ce JSON (rien d'autre):
{{
  "questions": [
    {{
      "question": "Texte de la question niveau 1",
      "choices": ["Choix A", "Choix B", "Choix C", "Choix D"],
      "answer_index": 0,
      "explanation": "Explication courte de la réponse correcte"
    }},
    // ... 4 autres objets identiques
  ]
}}

IMPORTANT: Ne génère que le JSON, aucun texte supplémentaire.
"""
    
    def _parse_quiz_response(self, raw_content, palier):
        """Parse et valide la réponse de l'API"""
        try:
            # Essayer de parser le JSON directement
            if isinstance(raw_content, str):
                data = json.loads(raw_content)
            else:
                data = raw_content
            
            # Valider la structure
            if "questions" not in data:
                # Peut-être que l'API a retourné directement le tableau
                if isinstance(data, list):
                    questions = data[:5]  # Prendre max 5 questions
                else:
                    raise ValueError("Format de réponse invalide")
            else:
                questions = data["questions"][:5]  # Limiter à 5 questions
            
            # Ajouter les métadonnées manquantes
            for i, q in enumerate(questions, 1):
                q["level"] = i
                q["palier"] = palier
                q["theme"] = PALIER_THEMES.get(palier, ["Général"])[0]  # Premier thème du palier
                q.setdefault("explanation", "Réponse correcte.")
                
                # Validation minimale
                if not all(key in q for key in ["question", "choices", "answer_index"]):
                    raise ValueError(f"Question {i} incomplète")
            
            return questions
            
        except json.JSONDecodeError as e:
            # Essayer d'extraire le JSON de la réponse textuelle
            print(f"Erreur de parsing JSON: {e}")
            print(f"Raw content: {raw_content}")
            return None
        except Exception as e:
            print(f"Erreur lors du parsing: {e}")
            return None
    
    def _generate_fallback_questions(self, palier):
        """Génère des questions de secours en cas d'erreur"""
        return [
            {
                "question": f"Palier {palier} - Question {i} (Quelle est la bonne réponse ?)",
                "choices": [f"Réponse A (correcte)", f"Réponse B", f"Réponse C", f"Réponse D"],
                "answer_index": 0,
                "level": i,
                "palier": palier,
                "theme": PALIER_THEMES.get(palier, ["Général"])[0],
                "explanation": "Cette question est générée automatiquement en attendant la version finale."
            }
            for i in range(1, 6)
        ]
    
    def generate_for_palier(self, age, topic, palier):
        """Génère les 5 questions d'un palier spécifique"""
        # Vérifier le cache d'abord
        cache_key = self._get_cache_key(age, topic, palier)
        cached = cache.get(cache_key)
        
        if cached:
            print(f" Quiz récupéré du cache: {cache_key}")
            return cached
        
        print(f" Génération du quiz pour palier {palier}...")
        
        try:
            # Construire le prompt
            prompt = self._build_complete_prompt(age, topic, palier)
            
            # Appeler l'API
            response = self.model.run([{"role": "user", "content": prompt}])
            
            # Vérifier les erreurs
            if response.output is None or response.error:
                print(f" Erreur API pour palier {palier}: {response.error}")
                questions = self._generate_fallback_questions(palier)
            else:
                # Parser la réponse
                raw_content = response.output.get("content", "")
                questions = self._parse_quiz_response(raw_content, palier)
                
                # Si parsing échoue, utiliser fallback
                if not questions:
                    print(f"  Parsing échoué pour palier {palier}")
                    questions = self._generate_fallback_questions(palier)
            
            # Mettre en cache
            cache.set(cache_key, questions, self.cache_timeout)
            print(f" Quiz généré et mis en cache: {cache_key}")
            
            return questions
            
        except Exception as e:
            print(f" Exception pour palier {palier}: {e}")
            questions = self._generate_fallback_questions(palier)
            cache.set(cache_key, questions, 300)  # Cache court pour les erreurs
            return questions

# Initialiser le générateur de quiz
quiz_generator = QuizGenerator(model)

# Fonctions de compatibilité (pour les appels existants si nécessaire)
def build_quiz_prompt(age, topic, palier, level):
    """Fonction maintenue pour compatibilité"""
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
    """Fonction maintenue pour compatibilité (utilise désormais le générateur)"""
    # Générer tout le palier et extraire la question demandée
    questions = quiz_generator.generate_for_palier(age, topic, palier)
    
    # Trouver la question du niveau demandé
    for q in questions:
        if q.get("level") == level:
            return {
                "question": q["question"],
                "choices": q["choices"],
                "answer_index": q["answer_index"]
            }
    
    # Fallback si non trouvé
    return {
        "question": f"Question {level} du palier {palier}",
        "choices": ["A", "B", "C", "D"],
        "answer_index": 0
    }

def build_quiz(age, topic):
    """Génère un quiz complet (10 paliers) - OPTIMISÉ"""
    quiz = {"age": age, "topic": topic, "paliers": []}
    
    for palier in range(1, 11):
        # Générer les 5 questions du palier
        questions = quiz_generator.generate_for_palier(age, topic, palier)
        
        palier_data = {
            "palier": palier,
            "levels": questions  # Contient déjà les 5 niveaux
        }
        
        quiz["paliers"].append(palier_data)
    
    return quiz

@csrf_exempt
def generate_quiz(request):
    """Vue optimisée pour générer un palier de quiz"""
    palier = int(request.POST.get("palier", 0))  # 0 = question d'attente
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
        # Génération optimisée du palier demandé (1 à 10)
        questions = quiz_generator.generate_for_palier(age, topic, palier)
        
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

"""
Creation de Systeme de recommandation
"""
# views.py - Ajoute ces fonctions après le code du quiz

import numpy as np
from django.db.models import Count, Q
from collections import defaultdict

class RecommendationEngine:
    """Moteur de recommandation optimisé"""
    
    def __init__(self):
        self.decay_factor = 0.95  # Facteur de dégradation des anciennes actions
        self.min_relevance = 0.1  # Seuil minimal de pertinence
        
    def update_user_preferences(self, user, post, action_type):
        """
        Met à jour les préférences utilisateur après un like/dislike
        action_type: 'like' ou 'dislike'
        """
        try:
            # Récupérer les tags du post
            tags = post.tags.all()
            
            # Poids selon l'action
            weight = 1.0 if action_type == 'like' else -0.5
            
            for tag in tags:
                # Mettre à jour ou créer la préférence
                pref, created = UserPreference.objects.get_or_create(
                    user=user,
                    tag=tag,
                    defaults={'score': weight}
                )
                
                if not created:
                    # Appliquer un facteur de décroissance pour les anciennes préférences
                    current_score = pref.score
                    decayed_score = current_score * self.decay_factor
                    
                    # Ajouter le nouveau poids (avec décroissance)
                    new_score = decayed_score + weight
                    
                    # Limiter les scores extrêmes
                    pref.score = max(-5.0, min(5.0, new_score))
                    pref.save()
            
            # Invalider le cache de recommandations
            self.invalidate_recommendation_cache(user)
            
            return True
            
        except Exception as e:
            print(f"Erreur mise à jour préférences: {e}")
            return False
    
    def invalidate_recommendation_cache(self, user):
        """Invalide le cache des recommandations pour un utilisateur"""
        cache_key = f"user_recommendations_{user.id}"
        cache.delete(cache_key)
        
        # Supprimer aussi les recommandations en base si existent
        PostRecommendation.objects.filter(user=user).delete()
    
    def get_user_preference_score(self, user, tag):
        """Récupère le score de préférence d'un utilisateur pour un tag"""
        try:
            pref = UserPreference.objects.get(user=user, tag=tag)
            return pref.score
        except UserPreference.DoesNotExist:
            return 0.0
    
    def calculate_post_relevance(self, user, post):
        """
        Calcule la pertinence d'un post pour un utilisateur
        Basé sur les tags, popularité et fraîcheur
        """
        if not user.is_authenticated:
            return self.calculate_baseline_relevance(post)
        
        try:
            relevance_score = 0.0
            
            # 1. Score basé sur les tags
            tag_score = 0.0
            tags = post.tags.all()
            
            if tags.exists():
                for tag in tags:
                    tag_score += self.get_user_preference_score(user, tag)
                
                # Normaliser par le nombre de tags
                tag_score = tag_score / len(tags)
            
            # 2. Score basé sur la popularité (likes - dislikes)
            like_count = post.likes.count()
            dislike_count = post.dislikes.count()
            popularity_score = (like_count - dislike_count) / max(1, like_count + dislike_count)
            
            # 3. Score basé sur la fraîcheur
            days_old = (timezone.now() - post.created_at).days
            freshness_score = 1.0 / (1 + days_old)  # Décroissance avec le temps
            
            # 4. Score de crédibilité (basé sur l'analyse IA et fake news)
            credibility_score = 0.0
            if post.made_ai is not None and post.fake_news is not None:
                # Moins de probabilité IA = mieux
                ai_score = 1.0 - (post.made_ai / 100.0)
                # Moins de fake news = mieux
                fake_score = 1.0 - (post.fake_news / 100.0)
                credibility_score = (ai_score + fake_score) / 2.0
            
            # Combinaison pondérée des scores
            relevance_score = (
                0.4 * tag_score +          # Préférences utilisateur
                0.2 * popularity_score +   # Popularité
                0.2 * freshness_score +    # Fraîcheur
                0.2 * credibility_score    # Crédibilité
            )
            
            return relevance_score
            
        except Exception as e:
            print(f"Erreur calcul pertinence: {e}")
            return 0.0
    
    def calculate_baseline_relevance(self, post):
        """Calcul de pertinence pour utilisateurs non connectés"""
        # Basé sur popularité et fraîcheur
        like_count = post.likes.count()
        dislike_count = post.dislikes.count()
        popularity_score = (like_count - dislike_count) / max(1, like_count + dislike_count)
        
        days_old = (timezone.now() - post.created_at).days
        freshness_score = 1.0 / (1 + days_old)
        
        return 0.7 * popularity_score + 0.3 * freshness_score
    
    def get_personalized_recommendations(self, user, limit=20):
        """
        Retourne les posts les plus pertinents pour un utilisateur
        Utilise le cache pour optimiser les performances
        """
        if not user.is_authenticated:
            # Pour utilisateurs non connectés, retourner les plus populaires
            return self.get_popular_posts(limit)
        
        cache_key = f"user_recommendations_{user.id}"
        cached_posts = cache.get(cache_key)
        
        if cached_posts:
            return cached_posts
        
        try:
            # Récupérer tous les posts (avec préfetch pour optimiser)
            posts = Post.objects.all().select_related(
                'author'
            ).prefetch_related(
                'tags', 'likes', 'dislikes'
            ).order_by('-created_at')[:200]  # Limiter pour performance
            
            # Calculer les scores de pertinence
            scored_posts = []
            for post in posts:
                score = self.calculate_post_relevance(user, post)
                if score >= self.min_relevance:
                    scored_posts.append((score, post))
            
            # Trier par score décroissant
            scored_posts.sort(key=lambda x: x[0], reverse=True)
            
            # Prendre les meilleurs
            recommended_posts = [post for score, post in scored_posts[:limit]]
            
            # Mettre en cache pour 1 heure
            cache.set(cache_key, recommended_posts, 3600)
            
            # Sauvegarder dans la base pour historique
            try:
                recommendation = PostRecommendation.objects.create(
                    user=user,
                    cache_key=cache_key
                )
                recommendation.recommended_posts.set(recommended_posts[:10])
            except:
                pass  # Ignorer les erreurs de sauvegarde historique
            
            return recommended_posts
            
        except Exception as e:
            print(f"Erreur recommandations: {e}")
            return self.get_fallback_posts(limit)
    
    def get_popular_posts(self, limit=20):
        """Posts populaires (likes - dislikes)"""
        try:
            # Annoter avec un score de popularité
            posts = Post.objects.annotate(
                popularity=Count('likes') - Count('dislikes')
            ).order_by('-popularity', '-created_at')[:limit]
            
            return list(posts)
        except:
            return self.get_fallback_posts(limit)
    
    def get_fallback_posts(self, limit=20):
        """Fallback: posts récents"""
        return list(Post.objects.all().order_by('-created_at')[:limit])

# Initialiser le moteur de recommandation
recommendation_engine = RecommendationEngine()
@login_required
@csrf_exempt
def toggle_like(request, post_id):
    """Gère les likes d'un post"""
    try:
        post = Post.objects.get(id=post_id)
        user = request.user
        
        if user in post.likes.all():
            # Retirer le like
            post.likes.remove(user)
            # Mettre à jour les préférences (annulation)
            recommendation_engine.update_user_preferences(user, post, 'unlike')
            liked = False
        else:
            # Ajouter le like et retirer le dislike si présent
            post.likes.add(user)
            if user in post.dislikes.all():
                post.dislikes.remove(user)
            # Mettre à jour les préférences
            recommendation_engine.update_user_preferences(user, post, 'like')
            liked = True
        
        # Retourner les nouveaux counts
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': post.likes.count(),
            'dislike_count': post.dislikes.count()
        })
        
    except Post.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Post not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
def toggle_dislike(request, post_id):
    """Gère les dislikes d'un post"""
    try:
        post = Post.objects.get(id=post_id)
        user = request.user
        
        if user in post.dislikes.all():
            # Retirer le dislike
            post.dislikes.remove(user)
            # Mettre à jour les préférences (annulation)
            recommendation_engine.update_user_preferences(user, post, 'undislike')
            disliked = False
        else:
            # Ajouter le dislike et retirer le like si présent
            post.dislikes.add(user)
            if user in post.likes.all():
                post.likes.remove(user)
            # Mettre à jour les préférences
            recommendation_engine.update_user_preferences(user, post, 'dislike')
            disliked = True
        
        # Retourner les nouveaux counts
        return JsonResponse({
            'success': True,
            'disliked': disliked,
            'like_count': post.likes.count(),
            'dislike_count': post.dislikes.count()
        })
        
    except Post.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Post not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def get_recommendations(request):
    """Retourne les posts recommandés"""
    if request.user.is_authenticated:
        posts = recommendation_engine.get_personalized_recommendations(request.user, limit=20)
    else:
        posts = recommendation_engine.get_popular_posts(limit=20)
    
    return render(request, 'post/recommendations.html', context={'posts': posts})

def get_user_preferences(request):

    """API pour récupérer les préférences de l'utilisateur (pour debugging)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    preferences = UserPreference.objects.filter(user=request.user).order_by('-score')[:10]
    
    data = [{
        'tag': pref.tag.name,
        'score': pref.score,
        'last_updated': pref.last_updated.strftime('%Y-%m-%d %H:%M')
    } for pref in preferences]
    
    return JsonResponse({'preferences': data})

