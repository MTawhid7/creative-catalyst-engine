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

1.  **Sync `main`:**
    ```bash
    git switch main
    git pull --rebase company main
    ```
2.  **Create Your Feature Branch:** Use our [Branch Naming Conventions](#branch-naming-conventions).
    ```bash
    git switch -c feat/add-image-watermarking
    ```

### Step 3: Daily Development Loop

1.  **Code & Commit:** Make small, logical commits. Follow our [Commit Message Conventions](#commit-message-conventions).
    ```bash
    git add .
    git commit -m "feat(images): Implement core watermarking function"
    ```
2.  **Push to Your Workshop:** Use your personal remote as a constant backup.
    ```bash
    git push -u origin feat/add-image-watermarking
    ```

### Step 4: Keeping Your Branch Synced

Keep your feature branch updated with the latest from `main` to prevent large conflicts later.

1.  **Fetch the latest official history:**
    ```bash
    git fetch company
    ```
2.  **Rebase your branch onto `main`:**
    ```bash
    git rebase company/main
    ```
3.  **Force-push the updated branch to your workshop:** This is required and safe after rebasing a personal feature branch.
    ```bash
    git push --force-with-lease origin feat/add-image-watermarking
    ```

### Step 5: Submitting for Review

1.  **Push to the Showroom:** Make your branch visible to the company.
    ```bash
    git push company feat/add-image-watermarking
    ```
2.  **Open a Pull Request** on the company's GitHub repo, following the [PR Conventions](#pull-request-pr-conventions).

### Step 6: Finalizing the Merge

1.  **Squash and Merge:** Once approved, merge the PR using the **"Squash and merge"** option.
2.  **Edit Commit Message:** Condense the commit history into a single, clear message that follows our conventions.

### Step 7: Post-Merge Cleanup

1.  **Sync `main`:**
    ```bash
    git switch main
    git pull --rebase company main
    ```
2.  **Update Your Personal `main`:**
    ```bash
    git push origin main
    ```
3.  **Delete the Merged Branch Everywhere:**
    ```bash
    git branch -d feat/add-image-watermarking
    git push origin --delete feat/add-image-watermarking
    git push company --delete feat/add-image-watermarking
    ```

---

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
