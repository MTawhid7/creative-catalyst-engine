# Contributing to the Creative Catalyst Engine

First off, thank you for taking the time to contribute! This document is a living guide to help you understand the project's architecture, workflows, and best practices.

## Table of Contents

- [Contributing to the Creative Catalyst Engine](#contributing-to-the-creative-catalyst-engine)
  - [Table of Contents](#table-of-contents)
  - [1. Project Setup](#1-project-setup)
  - [2. Core Development Workflow](#2-core-development-workflow)
    - [The Dual-Remote Setup](#the-dual-remote-setup)
    - [Starting a New Feature](#starting-a-new-feature)
    - [Daily Work: Committing and Pushing](#daily-work-committing-and-pushing)
    - [Keeping Your Branch Updated](#keeping-your-branch-updated)
    - [The Release Workflow: Submitting to the Company Repo](#the-release-workflow-submitting-to-the-company-repo)
  - [3. Git Command Cheat Sheet](#3-git-command-cheat-sheet)
  - [4. Architectural Guidelines](#4-architectural-guidelines)
    - [The "Strategy Pattern" for Image Generators](#the-strategy-pattern-for-image-generators)
    - [The "Fail Fast" Principle](#the-fail-fast-principle)
  - [5. Troubleshooting Common Issues](#5-troubleshooting-common-issues)
  - [6. Project Utilities](#6-project-utilities)
    - [Clearing the Cache](#clearing-the-cache)

---

## 1. Project Setup

Before you begin, make sure you have the project running locally.

1.  **Clone the repository:**
    ```bash
    # Use the company repository URL
    git clone git@github.com:Your-Company-Name/new-repository-name.git
    cd new-repository-name
    ```
2.  **Set up the environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Configure `.env`:** Copy the `.env.example` to `.env` and fill in your API keys.
4.  **Run the services:** You will need three separate terminals.
    -   **Terminal 1 (Redis):** `docker start creative-catalyst-redis`
    -   **Terminal 2 (Celery):** `celery -A api.worker.celery_app worker --loglevel=info -P eventlet`
    -   **Terminal 3 (API):** `uvicorn api.main:app --reload --port 9500 --host 0.0.0.0`

---

## 2. Core Development Workflow

This project uses a robust Git workflow to separate work-in-progress from stable, production-ready code.

### The Dual-Remote Setup

Your local repository is connected to two remotes:
-   `origin`: Your personal GitHub repository. This is your "workshop" for daily commits and backups.
-   `company`: The official company repository. This is for "shipping" final, approved features.

### Starting a New Feature

Never commit directly to `main` or `release`. Always create a new feature branch from the latest version of `main`.

```bash
# 1. Make sure your main branch is up-to-date
git checkout main
git pull origin main

# 2. Create and switch to your new feature branch
git checkout -b feat/my-new-feature
```
*(Branch naming convention: `feat/short-description`, `fix/bug-description`)*

### Daily Work: Committing and Pushing

Do your work on your feature branch. Commit your changes in small, logical steps and push frequently to your personal remote (`origin`) to back up your work.

```bash
# 1. Stage your changes
git add .

# 2. Commit with a clear message
git commit -m "feat: Implement the core logic for the new feature"

# 3. Push to your personal repository (origin)
git push origin feat/my-new-feature
```

### Keeping Your Branch Updated

To avoid difficult merges later, frequently update your feature branch with the latest changes from the main project. We prefer `rebase` over `merge` to maintain a clean, linear history.

```bash
# 1. Fetch the latest changes from the personal remote
git fetch origin

# 2. Rebase your branch on top of the latest main
git rebase origin/main
```
*(If you encounter conflicts, Git will guide you through resolving them. After resolving, run `git rebase --continue`.)*

### The Release Workflow: Submitting to the Company Repo

This is the formal process for submitting a completed feature.

1.  **Finalize your feature branch:** Ensure all code is tested and ready. Push any final commits to `origin`.

2.  **Merge into `main`:**
    ```bash
    # Switch to the main branch
    git checkout main

    # Pull the latest version to avoid conflicts
    git pull origin main

    # Merge your feature branch into main
    git merge --no-ff feat/my-new-feature

    # Push the updated main branch to your personal repo
    git push origin main
    ```

3.  **Merge into `release` and submit to the company:**
    ```bash
    # Switch to the release branch
    git checkout release

    # Pull the latest from the company repo (CRITICAL SAFETY STEP)
    git pull company release

    # Merge your updated main branch into release
    git merge main

    # Push the final, approved code to the company repository
    git push company release

    # Switch back to main to start your next task
    git checkout main
    ```

---

## 3. Git Command Cheat Sheet

Forgetting commands is normal. Here’s a quick reference.

| Task                                   | Command                                         |
| -------------------------------------- | ----------------------------------------------- |
| **Branching**                          |                                                 |
| See all local branches                 | `git branch`                                    |
| Create a new branch                    | `git branch <branch-name>`                      |
| Switch to a branch                     | `git checkout <branch-name>`                    |
| Create and switch in one step          | `git checkout -b <branch-name>`                 |
| Delete a local branch (safely)         | `git branch -d <branch-name>`                   |
| Delete a local branch (force)          | `git branch -D <branch-name>`                   |
| Delete a remote branch                 | `git push <remote-name> --delete <branch-name>` |
| **Syncing & Merging**                  |                                                 |
| See your remotes (`origin`, `company`) | `git remote -v`                                 |
| Push to a remote                       | `git push <remote-name> <branch-name>`          |
| Fetch latest from a remote             | `git fetch <remote-name>`                       |
| Pull (fetch + merge) from a remote     | `git pull <remote-name> <branch-name>`          |
| Merge another branch into current      | `git merge <branch-name>`                       |
| Rebase current branch onto another     | `git rebase <branch-name>`                      |
| **Cleaning Up**                        |                                                 |
| See the status of your files           | `git status`                                    |
| Discard changes to a file              | `git restore <file-path>`                       |
| Unstage a file (`git add .`)           | `git restore --staged <file-path>`              |
| Revert the last commit                 | `git reset --soft HEAD~1`                       |

---

## 4. Architectural Guidelines

### The "Strategy Pattern" for Image Generators

The image generation pipeline is designed to be modular. All generator code lives in `catalyst/pipeline/processors/generation/`.

-   **`base_generator.py`**: Defines the "contract" (`BaseImageGenerator`) that all generators must follow.
-   **`dalle3_generator.py`, etc.**: Concrete implementations for each model.
-   **`__init__.py`**: The "Factory" that selects which generator to use based on the `IMAGE_GENERATION_MODEL` in your `.env` file.

**To add a new model (e.g., "Apple Vision Pro 2"):**
1.  Create `apple_vp2_generator.py`.
2.  Create a class `AppleVP2Generation(BaseImageGenerator)` and implement the `generate_images` method.
3.  Add it to the factory in `__init__.py`.
4.  Update your `.env` file: `IMAGE_GENERATION_MODEL="apple-vp2"`.

### The "Fail Fast" Principle

Clients (`gemini_client.py`, `nanobanana_generator.py`, etc.) are initialized **eagerly** (on startup). If a critical configuration like an API key is missing, the client will fail to initialize and log a `CRITICAL` error immediately. The code then uses **guard clauses** (`if not self.client: ...`) to halt execution cleanly. This prevents the pipeline from running for minutes only to fail at the very end.

---

## 5. Troubleshooting Common Issues

-   **502 Bad Gateway / Could not connect:** This is a network issue.
    1.  Ensure the `uvicorn` API server is running.
    2.  If connecting from another machine, ensure you started the server with `--host 0.0.0.0` and are using the correct network IP address (e.g., `http://192.168.10.189:9500`), not `127.0.0.1`.
    3.  Check for firewalls blocking port `9500`.

-   **`AttributeError: 'NoneType' object has no attribute 'models'` (or similar):**
    *   This means a client (like the Gemini client) failed to initialize. **Check your Celery worker's startup log.** You will see a `CRITICAL` error message. The root cause is almost always a missing or incorrect API key in your `.env` file.

-   **API response has an empty `image_urls` list:**
    *   This means the image generation step was either disabled (`ENABLE_IMAGE_GENERATION=False`) or failed. **Check the Celery worker log** for the job's run ID. The log will contain the specific error traceback from the image generator.

---

## 6. Project Utilities

### Clearing the Cache

The project uses a ChromaDB cache to speed up runs with similar prompts. If you make major changes to the prompts or models, you may want to clear this cache to force a full re-synthesis.

Run this command from the project root:
```bash
python clear_cache.py
```
The script will ask for confirmation before deleting the cache directory.