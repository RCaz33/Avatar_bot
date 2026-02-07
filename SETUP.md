# 0 - set up infrastructure

```
#!/bin/bash

RESOURCE_GROUP="my-container-app-rg"
LOCATION="eastus"
ENVIRONMENT="my-environment"
API_NAME="my-album-api"
IMAGE_NAME="album-api-image"

az login
az extension add --name containerapp --upgrade --allow-preview true

az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

az group create --name $RESOURCE_GROUP --location $LOCATION

az containerapp up \
  --name "$API_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$ENVIRONMENT" \
  --source . 
```

----------------------------------------------

1. Get Subscription ID
2. Create the Service Principal and copy output to github secrets as AZURE_CREDENTIALS.

```
az account show --query id -o tsv

az ad sp create-for-rbac \
  --name "myContainerAppAutomation" \
  --role contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/album-containerapps \
  --sdk-auth
```
3. Generate a GitHub Personal Access Token (PAT) -- > GitHub Settings (User settings, not repo) > Developer settings > Tokens (classic). :: Generate a token with repo and workflow scopes.


# 1 - setup automation

https://learn.microsoft.com/en-us/cli/azure/containerapp/github-action?view=azure-cli-latest
az containerapp github-action add --help

* default
https://learn.microsoft.com/en-us/azure/container-apps/github-actions-cli?tabs=bash
```
az containerapp github-action add \
  --repo-url "https://github.com/<OWNER>/<REPOSITORY_NAME>" \
  --context-path "./dockerfile" \
  --branch <BRANCH_NAME> \
  --name <CONTAINER_APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --registry-url <URL_TO_CONTAINER_REGISTRY> \
  --registry-username <REGISTRY_USER_NAME> \
  --registry-password <REGISTRY_PASSWORD> \
  --service-principal-client-id <appId> \
  --service-principal-client-secret <password> \
  --service-principal-tenant-id <tenant> \
  --token <YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>

```

* template ready
https://github.com/marketplace/actions/azure-container-apps-build-and-deploy

```
az containerapp github-action add \
  --repo-url "https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>" \
  --name $API_NAME \
  --resource-group $RESOURCE_GROUP \
  --branch main \
  --token <YOUR_GITHUB_PAT_TOKEN>
```


# 2 - Add secrets to GitHub Repository settings (Settings > Secrets and variables > Actions)

AZURE_CREDENTIALS with
```
az ad sp create-for-rbac --sdk-auth
```
AZURE_TOKEN

(Optional) Your GitHub Personal Access Token if the CLI didn't handle it.


### deploy app with health check
```

az containerapp up \
  --name "$API_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$ENVIRONMENT" \
  --source . \
  --readiness-probe-path /albums \
  --readiness-probe-port 8080 \
  --readiness-probe-interval 10 \
  --readiness-probe-retries 3
```




  # 4 - GPU deploy

  check if region supports GPU profiles (eastus, westus3, or northeurope).

### 4.1 Create the Environment with a GPU-enabled Workload Profile
* Dedicated workload profile (fixed cost). Creates the environment and the workload profile in a single command. This is used for Dedicated hardware where you reserve the whole GPU.
https://learn.microsoft.com/en-us/cli/azure/containerapp/env?view=azure-cli-latest
```
az containerapp env create \
  --name "gpu-env" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --workload-profile-type "NC7jads_H100_v5" \
  --workload-profile-name "gpu-profile"
```

### 4.1b Create the environment in Paris
* New "Consumption" GPU model (pay-per-second, scales to zero).
https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview
```
az containerapp env create \
  --name "france-gpu-env" \
  --resource-group "my-rg" \
  --location "francecentral" \
  --enable-workload-profiles
```

### 4.1b Add the GPU profile (using the T4 as an example)
```
az containerapp env workload-profile add \
  --name "france-gpu-env" \
  --resource-group "my-rg" \
  --workload-profile-name "gpu-t4" \
  --workload-profile-type "Consumption" \
  --gpu-type "T4"
```

### 4.2 Deploy with GPU-enabled Workload profile
* --min-replicas 0: This enables Scale-to-Zero. 
* --workload-profile-name "gpu-t4": To avoid deploying to the standard "Consumption" tier which has no GPUs.
* --target-port 8080: Route traffic to port 8080 inside container. Flask or FastAPI must runs on 8080.
* --ingress 'external': This creates a public load balancer and a URL. Without this, your container is "dark" and cannot be reached from outside the Azure network.
* --query "properties.configuration.ingress.fqdn": This is a CLI print of the Domain Name (live URL).

```
az containerapp create \
  --name "ai-model-app" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "gpu-env" \
  --workload-profile-name "gpu-profile" \
  --cpu 2.0 --memory 8Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --image "your-registry.azurecr.io/ai-app:v1"

az containerapp create \
  --name "france-ai-service" \
  --resource-group "my-rg" \
  --environment "france-gpu-env" \
  --workload-profile-name "gpu-t4" \
  --image "myregistry.azurecr.io/ai-app:v1" \
  --target-port 8080 \
  --ingress 'external' \
  --min-replicas 0 \
  --max-replicas 3 \
  --cpu 2.0 --memory 8Gi \
  --query "properties.configuration.ingress.fqdn"
```

# 5 - ATTENTION

3. Important "Legit" Reality Checks

When dealing with GPUs in Azure, keep these three things in mind:

    Quota Limits: Most new Azure accounts have a 0 quota for GPU cores. You will likely see an error message saying "Quota exceeded." You must go to the Azure Portal and "Request Quota Increase" for the specific VM series (like NCv3) in your region.

    Cost: Unlike the "Consumption" tier which scales to zero, Dedicated Workload Profiles charge you as long as the profile is active, even if the container isn't doing anything. It's much more expensive than the "Code-to-Cloud" quickstart.

    Drivers: Azure Container Apps manages the NVIDIA drivers for you. You just need to ensure your Docker image has the CUDA toolkit installed (use a base image like nvidia/cuda).