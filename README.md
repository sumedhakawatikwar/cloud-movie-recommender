### Instructions to setup (In Local):- 

-> Setup streamlit environment

1. Inside project folder, python3 -m pip install --user virtualenv

2. python3 -m pip install --user virtualenv

3. source env/bin/activate

4. pip install streamlit

5. pip install redis

6. pip install flask

7. pip install jsonpickle

    -> Setup gcloud redis/rabbitmq

    1. gcloud config set compute/zone us-central1-b
    2. gcloud config set project southern-surge-289519
    3. gcloud container clusters create --preemptible mykube
    4. ./deploy-local-dev.sh
    5. (Later delete cluster if needed) gcloud container clusters delete mykube

8. cd rest/ python3 recommendation_rest_server.py

9. streamlit run filename.py

 Running on http://127.0.0.1:5000
 Running on http://172.20.0.3:5000

7. Finally, deactivate if required


-> Setup kubernetes in local (if needed)

1. curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"
2. chmod +x ./kubectl
3. sudo mv ./kubectl /usr/local/bin/kubectl


### Deployment on GKE (GCP)

-> Dataset - Download and unzip dataset from https://grouplens.org/datasets/movielens/25m/ in rest/dataset

-> docker build -t gcr.io/southern-surge-289519/recc-rest -f /home/amro9884/Cloud-Based-Movie-Recommender-System/rest/Dockerfile-rest .

-> docker push gcr.io/southern-surge-289519/recc-rest:latest

-> kubectl apply -f rest-deployment.yaml

-> kubectl apply -f rest-service.yaml

-> docker build -t gcr.io/southern-surge-289519/recc-app -f /home/amro9884/Cloud-Based-Movie-Recommender-System/Dockerfile-app .

-> docker push gcr.io/southern-surge-289519/recc-app:latest

-> kubectl apply -f app-deployment.yaml

-> kubectl apply -f app-ingress-backendconfig.yaml

-> (to delete backend config) - kubectl delete backendconfig app-ingress-backendconfig

-> kubectl apply -f app-service.yaml

Ingress - gcloud container clusters update mykube --update-addons=HttpLoadBalancing=ENABLED

-> kubectl apply -f app-ingress.yaml


