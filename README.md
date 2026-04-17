---
title: Avatar Bot
emoji: 👀
colorFrom: green
colorTo: indigo
sdk: gradio
sdk_version: 6.3.0
app_file: app.py
pinned: false
hf_oauth: true
hf_oauth_scopes:
- inference-api
short_description: a bot that answer questions about professional projets
license: mit
---

# A chatbot with rag for curriculum vitae

Because informations contained in the vector might be confidential, we prepare it locally, encrypt it with a key saved on azure keyvault and upload the encrypted vector store to blob.

Now the running app iun container load the encrypted file and decrypt it with a call on azure so it can be use in the bot answering pipeline.

Docker Container
- run local macos (arm64 mps)
- run cloud cpu / docker actions
        during docker build, precise adm64
        reqs --extra-index-url https://download.pytorch.org/whl/cpu torch faiss-cpu

- run cloud gpu, use cuda image and precise amd64


# A chatbot with rag for curriculum vitae

Because informations contained in the vector might be confidential, we prepare it locally, encrypt it with a key saved on azure keyvault and upload the encrypted vector store to blob.

Now the running app iun container load the encrypted file and decrypt it with a call on azure so it can be use in the bot answering pipeline.

Docker Container
- run local macos (arm64 mps)
- run cloud cpu / docker actions
        during docker build, precise adm64
        reqs --extra-index-url https://download.pytorch.org/whl/cpu torch faiss-cpu

- run cloud gpu, use cuda image and precise amd64


# Branching strategy
- origin on git@github.com named 'github' --> prod ready

        # make modif
        git checkout -b feature-xyz
        git add x y z
        git commit -m "why and how this feature"
        # health chek
        git checkout prod_ready
        git pull github prod_ready
        git checkout feature-xyz
        git merge prod_ready
        # push on hub
        git push github feature-xyz
        on github: create pull request

- origin on git@hf.co:spaces named 'origin' --> main

        # create PR on spaces / make changes locally
        git fetch origin refs/pr/17:pr/17
        git checkout pr/17
        # modify and commit
        git push origin pr/17:refs/pr/17
        # On Spaces go to "Community" tab
        # find PR and publish then merge