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

An chatbot with rag for curriculum vitae

Container

local macos (arm64 mps)

cloud cpu / docker actions
during docker build, precise adm64
reqs --extra-index-url https://download.pytorch.org/whl/cpu torch faiss-cpu

cloud gpu
