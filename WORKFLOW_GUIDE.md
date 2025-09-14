# The Definitive Git Workflow Guide

Welcome to the official development workflow for the Creative Catalyst Engine. This guide is the single source of truth for how we write, review, and submit code. Following these steps ensures our project history remains clean, our code stays stable, and our collaboration is efficient and safe.

---

## Table of Contents

- [The Definitive Git Workflow Guide](#the-definitive-git-workflow-guide)
  - [Table of Contents](#table-of-contents)
  - [Phase 1: The Core Workflow](#phase-1-the-core-workflow)
    - [The Golden Rule: Workshop vs. Showroom](#the-golden-rule-workshop-vs-showroom)
    - [Step 1: One-Time Setup](#step-1-one-time-setup)
    - [Step 2: Starting a New Task](#step-2-starting-a-new-task)
    - [Step 3: Daily Development Loop](#step-3-daily-development-loop)
    - [Step 4: Keeping Your Branch Synced](#step-4-keeping-your-branch-synced)
    - [Step 5: Submitting for Review](#step-5-submitting-for-review)
    - [Step 6: Finalizing the Merge](#step-6-finalizing-the-merge)
    - [Step 7: Post-Merge Cleanup](#step-7-post-merge-cleanup)
  - [Phase 2: Release \& Tagging Workflow](#phase-2-release--tagging-workflow)
    - [Step 1: Prepare the Release](#step-1-prepare-the-release)
    - [Step 2: Create the Signed Tag (Manual Process)](#step-2-create-the-signed-tag-manual-process)
    - [Step 3: Push the Tag to Remotes](#step-3-push-the-tag-to-remotes)
  - [Phase 2: Philosophy \& Conventions](#phase-2-philosophy--conventions)
    - [Our Guiding Principles (The "Why")](#our-guiding-principles-the-why)
    - [Branch Naming Conventions](#branch-naming-conventions)
    - [Commit Message Conventions](#commit-message-conventions)
    - [Pull Request (PR) Conventions](#pull-request-pr-conventions)
  - [Phase 3: Scenarios \& Recovery (The "Oh No!" Guide)](#phase-3-scenarios--recovery-the-oh-no-guide)
    - [Scenario 1: Fix a typo or add a file to the last commit](#scenario-1-fix-a-typo-or-add-a-file-to-the-last-commit)
    - [Scenario 2: Clean up a messy branch before a PR](#scenario-2-clean-up-a-messy-branch-before-a-pr)
    - [Scenario 3: Escape a rebase with a major conflict](#scenario-3-escape-a-rebase-with-a-major-conflict)
    - [Scenario 4: Accidentally committed to `main`](#scenario-4-accidentally-committed-to-main)
  - [Strategic Command Reference](#strategic-command-reference)
---

## Phase 1: The Core Workflow

This is the end-to-end process for taking a task from idea to merged reality.

### The Golden Rule: Workshop vs. Showroom

-   **Your Personal Public Repo (`origin`):** This is your **Workshop**. It's your private, safe space to experiment, make messes, and save your daily progress. Pushing here is frequent and informal.
-   **The Private Company Repo (`company`):** This is the **Official Showroom**. It is the single source of truth for the project. Code only enters the showroom after it is complete, tested, and formally approved via a Pull Request.

### Step 1: One-Time Setup

**Goal:** Configure your local machine to correctly interact with both repositories. You only need to do this once.

1.  **Clone the Private Company Repository:**
    ```bash
    git clone <company-repo-url> CreativeCatalystEngine && cd CreativeCatalystEngine
    ```
2.  **Add Your Public Personal Repo as a Remote:**
    ```bash
    git remote add origin <your-personal-repo-url>
    ```
3.  **Rename the Original Remote to `company`:**
    ```bash
    git remote rename origin company
    ```
4.  **Verify Your Remotes:** Run `git remote -v`. You should see both `company` and `origin` listed.
5.  **Set the Upstream for Your `main` Branch:**
    ```bash
    git switch main
    git branch --set-upstream-to=company/main
    ```

### Step 2: Starting a New Task

1.  **Create Your Feature Branch:** Use our [Branch Naming Conventions](#branch-naming-conventions).
    ```bash
    make new-branch b=feat/add-image-watermarking
    ```
    This command automatically syncs your `main` branch before creating the new feature branch.

### Step 3: Daily Development Loop

1.  **Code & Commit (Manual):** Make small, logical commits. This step remains manual to ensure high-quality, human-written commit messages. Follow our [Commit Message Conventions](#commit-message-conventions).
    ```bash
    git add .
    git commit -m "feat(images): Implement core watermarking function"
    ```
2.  **Push to Your Workshop (Automated):** Use your personal remote as a constant backup.
    ```bash
    make save
    ```

### Step 4: Keeping Your Branch Synced

Keep your feature branch updated with the latest from `main` to prevent large conflicts later.
```bash
make sync-branch
```
*(Note: This command will still require you to manually resolve any merge conflicts that arise during the rebase.)*

### Step 5: Submitting for Review

```bash
make submit
```
After running this, open a Pull Request on the company's GitHub repo, following the [PR Conventions](#pull-request-pr-conventions).

### Step 6: Finalizing the Merge

1.  **Squash and Merge:** Once approved, merge the PR using the **"Squash and merge"** option in the GitHub UI.
2.  **Edit Commit Message:** Condense the commit history into a single, clear message that follows our conventions.

### Step 7: Post-Merge Cleanup

```bash
make cleanup-branch b=feat/add-image-watermarking
```
This command automatically syncs your `main` branch before deleting the feature branch from your local machine and both remotes.

---

## Phase 2: Release & Tagging Workflow

### Step 1: Prepare the Release
**Sync the `release` Branch:** Run the `make release` command to merge all the latest changes from `main` into your `release` branch.
```bash
make release
```

### Step 2: Create the Signed Tag (Manual Process)
Creating a release tag is a significant, human-centric event. It is done manually to ensure a high-quality, detailed release message.

1.  **Switch to the `release` branch:** `git switch release`
2.  **Run the annotated, signed tag command:** Replace `v1.2.3` with the new version.
    ```bash
    git tag -s v1.2.3
    ```
3.  **Write a High-Quality Tag Message:** Your text editor will open. The message should be a concise changelog for the new version.

    **Example:**
    ```
    Release v1.2.3

    This release finalizes the migration to a fully containerized,
    asyncio-native architecture and hardens the application.

    ### Features
    - Migrated from Celery to ARQ for improved stability.
    - Containerized the full application stack with Docker Compose.
    - Implemented Sentry for real-time error monitoring.

    ### Fixes
    - Resolved the ChromaDB "database is locked" race condition.
    ```
4.  **Save and close the editor** to create the tag.

### Step 3: Push the Tag to Remotes
```bash
git push company v1.2.3
git push origin v1.2.3
```

## Phase 2: Philosophy & Conventions

### Our Guiding Principles (The "Why")

*   **A Clean History is Paramount:** Our primary goal is a linear, readable, and logical project history. This makes debugging, bisecting, and understanding the evolution of the codebase vastly simpler. This is why we prefer rebase over merge for feature branches and squash-and-merge for PRs.
*   **Commit Early, Commit Often, Push Constantly:** Treat `git push origin <branch>` as your personal "save" button. It protects you from local data loss and has no impact on the company repository.
*   **Keep `main` Pristine:** Your local `main` branch should always be a perfect mirror of the official `company/main`. Never commit directly to it.
*   **PRs are Small and Focused:** A Pull Request should do one thing and do it well. Small PRs are easier to review, less risky to merge, and lead to a more agile development process.

### Branch Naming Conventions

**Format:** `type/short-description` (e.g., `feat/add-image-watermarking`)
-   `feat`: A new feature for the user.
-   `fix`: A bug fix for the user.
-   `docs`: Changes to documentation.
-   `style`: Formatting, missing semi-colons, etc.; no code change.
-   `refactor`: A code change that neither fixes a bug nor adds a feature.
-   `test`: Adding or correcting tests.
-   `chore`: Changes to the build process or auxiliary tools.

### Commit Message Conventions

We follow the **[Conventional Commits](https://www.conventionalcommits.org/)** standard. This allows for automated changelog generation and a searchable history.
**Format:** `<type>(<scope>): <subject>`
-   **Example:** `fix(gemini-client): Add guard clause to prevent auth crash`

### Pull Request (PR) Conventions

-   **Title:** Should be a clean, descriptive summary following the commit message convention.
-   **Description:** Briefly explain the "what" and "why" of the change. Include clear steps for how to test the changes.

---

## Phase 3: Scenarios & Recovery (The "Oh No!" Guide)

Mistakes happen. This section covers the most common scenarios and their solutions.

### Scenario 1: Fix a typo or add a file to the last commit

1.  `git add <forgotten-file>`
2.  `git commit --amend --no-edit`
3.  `git push --force-with-lease origin <branch>`

### Scenario 2: Clean up a messy branch before a PR

Use an interactive rebase to squash, fixup, and reword your commits into a clean, logical sequence.

1.  `git rebase -i company/main`
2.  Follow the instructions in the editor to reorder, `squash` (s), or `fixup` (f) your commits.

### Scenario 3: Escape a rebase with a major conflict

If a rebase goes wrong, you can always get back to where you started.
```bash
git rebase --abort
```

### Scenario 4: Accidentally committed to `main`

1.  Save your work to a new branch: `git switch -c feat/my-saved-work`
2.  Reset your `main` branch back to the official version (this is a destructive command):
    ```bash
    git switch main
    git reset --hard company/main
    ```

---

## Strategic Command Reference

| Command                          | Use Case / When to Use It                                          |
| :------------------------------- | :----------------------------------------------------------------- |
| `git switch -c <branch>`         | At the start of a new task.                                        |
| `git push origin <branch>`       | Frequently, as your personal backup.                               |
| `git pull --rebase company main` | To sync your local `main` or update your feature branch.           |
| `git commit --amend`             | To fix your *most recent* commit before pushing to the company.    |
| `git rebase -i company/main`     | To clean up your entire branch history before a PR.                |
| `git rebase --abort`             | Your escape hatch for a failed rebase.                             |
| `git stash`                      | To quickly save uncommitted work when you need to change branches. |
