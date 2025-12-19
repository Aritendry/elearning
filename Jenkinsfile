pipeline {
    agent any

    environment {
        TEAM_NAME = "${env.JOB_NAME}"
        DOMAIN = "insi.local"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ Code récupéré"
            }
        }

        stage('Vérification Docker') {
            steps {
                sh '''
                    set -e
                    docker --version
                    docker compose version
                '''
            }
        }

        stage('Génération Traefik (auto)') {
            steps {
                sh '''
                    set -e
                    echo "⚙️ Génération config Traefik (override)..."

                    cat <<'EOF' > docker-compose.traefik.yml
services:
  web:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${TEAM_NAME}.rule=Host(`${TEAM_NAME}.${DOMAIN}`)"
      - "traefik.http.routers.${TEAM_NAME}.entrypoints=websecure"
      - "traefik.http.routers.${TEAM_NAME}.tls=true"
      - "traefik.http.services.${TEAM_NAME}.loadbalancer.server.port=3000"
    networks:
      - traefik-network

networks:
  traefik-network:
    external: true
EOF

                    echo "📄 Contenu docker-compose.traefik.yml"
                    cat docker-compose.traefik.yml
                '''
            }
        }

        stage('Déploiement') {
            steps {
                sh '''
                    set -e

                    if [ ! -f docker-compose.yml ] && [ ! -f compose.yml ]; then
                        echo "❌ Aucun fichier docker-compose trouvé"
                        exit 1
                    fi

                    echo "🛑 Arrêt anciens conteneurs..."
                    docker compose down -v || true

                    echo "🔨 Build..."
                    docker compose \
                      -f docker-compose.yml \
                      -f docker-compose.traefik.yml \
                      build --no-cache

                    echo "🚀 Démarrage..."
                    docker compose \
                      -f docker-compose.yml \
                      -f docker-compose.traefik.yml \
                      up -d

                    sleep 10
                    docker compose ps
                '''
            }
        }

        stage('Healthcheck') {
            steps {
                sh '''
                    echo "❤️ Vérification santé..."
                    docker compose ps
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Déploiement réussi → https://${TEAM_NAME}.${DOMAIN}"
        }
        failure {
            echo "❌ Échec du déploiement"
            sh 'docker compose logs || true'
        }
        always {
            echo "🏁 Pipeline terminé"
        }
    }
}
