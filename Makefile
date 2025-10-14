# Makefile for the Creative Catalyst Engine
#
# This file is the central command center for the project. It provides simple,
# memorable aliases for all common development, maintenance, and release operations.
# To see a list of all available commands, run: make help

# ===================================================================
#  CONFIGURATION & VARIABLES
# ===================================================================

# This variable defaults to the project's directory name, making commands more robust.
COMPOSE_PROJECT_NAME ?= creativecatalystengine
# This magic gets the current git branch name for use in git commands.
CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)

.PHONY: help \
	up down build build-clean \
	restart restart-api restart-worker \
	logs logs-api logs-worker \
	shell test sync-venv debug run-client \
	sync-main new-branch save sync-branch submit cleanup-branch \
	deps clear-cache scan clean-docker clean-docker-full clean-build-cache \
	release tag

# This sets the default command to 'help' if 'make' is run without arguments.
.DEFAULT_GOAL := help

# ===================================================================
#  HELP
# ===================================================================

help:
	@echo "=================================================================="
	@echo " 🚀 Creative Catalyst Engine - Command Center"
	@echo "=================================================================="
	@echo ""
	@echo " Usage: make <command>"
	@echo ""
	@echo " 🐳 Docker Lifecycle:"
	@echo "   up             Start all application services (API, worker, etc.)."
	@echo "   down           Stop and remove all application services."
	@echo "   build          Build (or rebuild) all Docker images using the cache."
	@echo "   build-clean    Force a clean rebuild of all images, ignoring the cache."
	@echo ""
	@echo " ☀️  Daily Development Workflow:"
	@echo "   restart-worker Restart only the worker service after a code change."
	@echo "   logs-worker    Tail the logs for only the worker service."
	@echo "   shell          Open an interactive shell inside the running worker container."
	@echo "   test           Run the full test suite inside a fresh Docker container."
	@echo "   sync-venv     Sync your local virtual environment with the lockfiles."
	@echo "   debug          Start all services in interactive debugging mode for VS Code."
	@echo ""
	@echo "   run-client     Run the example API client to submit a job locally."
	@echo ""
	@echo "   Git Workflow:"
	@echo "   sync-main      Sync your local 'main' branch with BOTH remotes."
	@echo "   new-branch     Create a new feature branch from latest 'main' (e.g., make new-branch b=feat/new-thing)."
	@echo "   save           Push the current branch to your personal remote ('origin')."
	@echo "   sync-branch    Rebase the current branch on the latest 'main'."
	@echo "   submit         Push the current branch to the company remote for a PR."
	@echo "   cleanup-branch Clean up a merged branch everywhere (e.g., make cleanup-branch b=feat/old-thing)."
	@echo ""
	@echo " 🧹 Project Maintenance:"
	@echo "   deps           Update and freeze Python dependencies using pip-tools."
	@echo "   clear-cache    Run the master script to clear all app caches (Redis, Chroma, files)."
	@echo "   scan           Scan the final API image for high-severity vulnerabilities."
	@echo "   clean-docker   (Safe) Clean unused Docker images, networks, and build caches."
	@echo "   clean-docker-full (Destructive) Clean everything, including data volumes."
	@echo ""
	@echo " 🚢 Release Management:"
	@echo "   release        Merge the main branch into the release branch safely."
	@echo "   tag            Display instructions for the manual tagging process."
	@echo ""


# ===================================================================
#  DOCKER LIFECYCLE
# ===================================================================

up:
	@echo "🚀 Starting all 'app' services (API, worker, Redis, Chroma)..."
	docker compose --profile app up

down:
	@echo "🛑 Stopping and removing all services..."
	docker compose --profile app down --remove-orphans

build:
	@echo "🏗️  Building the application Docker image..."
	docker compose --profile app build

build-clean:
	@echo "🏗️  Performing a clean build of the application image..."
	docker compose --profile app build --no-cache

# ===================================================================
#  DAILY DEVELOPMENT WORKFLOW
# ===================================================================

restart-api:
	@echo "🔄 Restarting the API service..."
	docker compose --profile app restart api

restart-worker:
	@echo "🔄 Restarting the worker service..."
	docker compose --profile app restart worker

logs-api:
	@echo "📜 Tailing logs for the API service..."
	docker compose --profile app logs -f api

logs-worker:
	@echo "📜 Tailing logs for the worker service..."
	docker compose --profile app logs -f worker

shell:
	@echo "🐚 Opening a shell inside the running worker container..."
	docker compose --profile app exec worker sh

test:
	@echo "🧪 Running unit and integration tests inside a clean container..."
	docker compose run --rm --entrypoint="" tester python -m pytest

sync-venv:
	@echo "🔄 Syncing your local virtual environment with the lockfiles..."
	@echo "   (Ensure your local virtual environment is active: 'source venv/bin/activate')"
	pip-sync requirements.txt dev-requirements.txt
	@echo "✅ Local venv is now in sync."

debug:
	@echo "🐞 Starting services in debug mode for VS Code attachment..."
	docker compose --profile app -f docker-compose.yml -f docker-compose.debug.yml up --build

# --- START: THE DEFINITIVE NETWORKING FIX ---
run-client:
	@echo "🚀 Running the example API client inside a container to submit a job..."
	docker compose run --rm \
		-e CREATIVE_CATALYST_API_URL="http://api:9500" \
		--entrypoint="" \
		api python3 -m api_client.example
# --- END: THE DEFINITIVE NETWORKING FIX ---

# ===================================================================
#  GIT WORKFLOW
# ===================================================================

sync-main:
	@echo "🔄 Syncing the local 'main' branch with BOTH remotes..."
	git switch main
	@echo "   Pulling latest from company..."
	git pull --rebase company main
	@echo "   Pushing latest to personal remote (origin)..."
	git push origin main

new-branch:
ifndef b
	$(error b is not set. Usage: make new-branch b=feat/my-new-feature)
endif
	@echo "🌱 Creating new branch '$(b)' from the latest 'main'..."
	make sync-main
	git switch -c $(b)

save:
	@echo "💾 Saving current branch '$(CURRENT_BRANCH)' to your personal remote (origin)..."
	git push -u origin $(CURRENT_BRANCH)

sync-branch:
	@echo "🔄 Syncing current branch '$(CURRENT_BRANCH)' with the latest 'main'..."
	git fetch company
	@echo "   (Note: Rebase may require you to resolve conflicts)"
	git rebase company/main
	git push --force-with-lease origin $(CURRENT_BRANCH)

submit:
	@echo "🚀 Submitting branch '$(CURRENT_BRANCH)' to the company remote for PR..."
	git push company $(CURRENT_BRANCH)

cleanup-branch:
ifndef b
	$(error b is not set. Usage: make cleanup-branch b=feat/my-merged-feature)
endif
	@echo "🧹 Cleaning up merged branch '$(b)' everywhere..."
	make sync-main
	git branch -d $(b)
	git push origin --delete $(b)
	git push company --delete $(b)

# ===================================================================
#  PROJECT MAINTENANCE & RELEASE
# ===================================================================

deps:
	@echo "📦 Updating and freezing dependencies..."
	@echo "   (Ensure your local virtual environment is active)"
	pip-compile --strip-extras requirements.in
	pip-compile --strip-extras dev-requirements.in
	@echo "✅ Lockfiles generated. Installing development dependencies into local venv..."
	pip-sync requirements.txt dev-requirements.txt

clear-cache:
	@echo "🔥 Clearing all application caches (Redis, Chroma, and files)..."
	docker compose --profile tasks --profile app run --rm clear-cache

scan: build
	@echo "🛡️  Scanning final API image for vulnerabilities..."
	trivy image --severity HIGH,CRITICAL $(COMPOSE_PROJECT_NAME)-api:latest

clean-docker: down
	@echo "🧹 (Safe) Pruning unused Docker images, networks, and build caches..."
	docker system prune -a
	docker buildx prune

clean-docker-full: down
	@echo "💣 (Destructive) Pruning everything, including data volumes..."
	docker system prune -a --volumes

release:
	@echo "🚢 Safely merging main into release..."
	git switch main
	git pull --rebase company main
	git switch release
	git pull --rebase company release
	git merge main
	git push company release
	git switch main

tag:
	@echo "🏷️  Tagging is a manual process to ensure high-quality release notes."
	@echo "   Please see the 'Release & Tagging Workflow' section in WORKFLOW_GUIDE.md"