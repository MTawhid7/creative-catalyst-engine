# The Definitive Git Workflow Guide

Welcome to the official development workflow for the Creative Catalyst Engine. This guide is the single source of truth for how we write, review, and submit code. Following these steps ensures our project history remains clean, our code stays stable, and our collaboration is efficient and safe.

### The Golden Rule: The Workshop vs. The Showroom

To understand this workflow, you only need to remember one core concept:

-   **Your Personal Public Repo (`origin`):** This is your **Workshop**. It's your private, safe space to experiment, make messes, and save your daily progress. Pushing here is frequent and informal.
-   **The Private Company Repo (`company`):** This is the **Official Showroom**. It is the single source of truth for the project. Code only enters the showroom after it is complete, tested, and formally approved via a Pull Request.

### Key Branches & Their Purpose

-   **`feature` branches (e.g., `feat/add-new-model`):** Temporary "drafts" where all new work happens. They are created locally and deleted after being merged.
-   **`main` branch:** The primary integration branch. It represents the latest, stable, development-ready version of the project. **Direct pushes to this branch are forbidden.**
-   **`release` branch:** A highly stable branch that is a "snapshot" of `main` at a specific point in time. It represents the "shippable" or "production-ready" version of the code.

---

## Phase 1: The One-Time Setup

**Goal:** Configure your local machine to correctly interact with both repositories. You only need to do this once.

> **Why this setup?** Because the company's repository is private, a standard public fork is not possible. This two-remote approach allows you to back up your work to your public personal repository (`origin`) while contributing to the private company repository (`company`).

1.  **Clone the Private Company Repository:**
    ```bash
    git clone <company-repo-url> CreativeCatalystEngine
    cd CreativeCatalystEngine
    ```

2.  **Add Your Public Personal Repo as a Remote:**
    ```bash
    git remote add origin <your-personal-repo-url>
    ```

3.  **Rename the Original Remote to `company`:** (The default name is `origin`)
    ```bash
    git remote rename origin company
    ```

4.  **Verify Your Remotes:** Run `git remote -v`. You should see both `company` (fetch/push) and `origin` (fetch/push) listed.

5.  **Set the Upstream for Your `main` Branch:** This critical step tells Git to compare your local `main` against the company's `main`.
    ```bash
    # Use the modern 'switch' command to change branches
    git switch main
    git branch --set-upstream-to=company/main
    ```

---

## Phase 2: The Core Feature Workflow Cycle

This is the end-to-end process for taking a task from idea to completion.

### Step 1: Start of Day / Start of New Task

**Goal:** Sync your local machine with the official project before writing any code.

1.  **Switch to your local `main` branch.**
    ```bash
    git switch main
    ```
2.  **Pull the latest official code using a rebase.** This avoids messy merge commits on your local `main`.
    ```bash
    # The --rebase flag ensures you maintain a clean, linear history
    git pull --rebase company main
    ```
3.  **Create and switch to your new feature branch.**
    ```bash
    # Use 'switch -c' to create a new branch and switch to it
    git switch -c feat/add-image-watermarking
    ```

### Step 2: Daily Development (The "Code, Commit, Push" Loop)

**Goal:** Write code and safely back it up to your personal "Workshop" repo.

1.  **Write and Test Your Code** on your feature branch.
2.  **Commit Your Changes** in small, logical units, following the [Commit Message Conventions](#2-commit-message-convention).
    ```bash
    git add .
    git commit -m "feat: Implement the core watermarking function"
    ```
3.  **Push to Your Personal Repo (`origin`)**. This is your backup. The `company` repo is not yet affected. The `-u` flag sets up the branch to track `origin`.
    ```bash
    git push -u origin feat/add-image-watermarking
    ```

### Step 3: Keeping Your Branch Synced (Rebasing)

**Goal:** Keep your feature branch updated with the latest changes from the official `main` branch to maintain a clean history and prevent complex merge conflicts later.

> **Why Rebase?** Rebasing rewrites your branch's history to make it look like you started your work from the most recent version of the project. This avoids messy "merge bubbles" and creates a clean, straight, linear history that is much easier to read and debug.

1.  **Fetch the latest history from the `company` remote.**
    ```bash
    git fetch company
    ```
2.  **Rebase your branch onto the official `main`.**
    ```bash
    git rebase company/main
    ```
3.  **Force-push the updated branch to your personal remote.** This is required and safe after rebasing a feature branch that only you are working on.
    ```bash
    git push --force-with-lease origin feat/add-image-watermarking
    ```

### Step 4: Submitting Your Work for Review (The Pull Request)

**Goal:** Formally propose your completed feature for inclusion in the official project.

1.  **Push your feature branch to the `company` remote.** This makes your work visible inside the company project and enables you to open a PR.
    ```bash
    git push company feat/add-image-watermarking
    ```
2.  **Open a Pull Request (PR) on the Company's GitHub Repo.** A banner for your recently pushed branch will automatically appear. Click **"Compare & pull request"**.
3.  **Write a clear title and a detailed description.** Follow the [Pull Request Conventions](#3-pull-request-pr-convention).
4.  **Assign teammates as Reviewers.**

### Step 5: Handling the Code Review Conversation

**Goal:** Collaboratively refine your code based on team feedback.

-   **If they request changes:** Make the changes on your local feature branch, commit, and push to both `origin` (for backup) and `company` (to update the PR). The PR will automatically show your new commits.
-   **If you disagree with a suggestion:** Reply to the comment on GitHub. Respectfully explain your reasoning with evidence. The goal is a technical discussion to find the best solution.

### Step 6: Finalizing the Merge (Best Practice: Squash and Merge)

**Goal:** Officially add your feature to the project with a clean, single commit on the `main` branch.

1.  **Merge the PR using "Squash and Merge":** Once the Pull Request is approved, click the **dropdown arrow** on the green merge button. Select **"Squash and merge"**.
2.  **Edit the Commit Message:** Condense the automatically generated list of commits into a single, clear message that follows our [Commit Message Conventions](#2-commit-message-convention).
3.  **Confirm the merge.**

### Step 7: The "Sync Back" and Final Cleanup

**Goal:** To reset your entire workspace to a clean state after your feature has been officially merged.

1.  **Switch back to `main` and update it.**
    ```bash
    git switch main
    git pull --rebase company main
    ```
2.  **Update your personal remote's `main` branch.**
    ```bash
    git push origin main
    ```
3.  **Delete the merged feature branch from all locations.**
    ```bash
    # Delete local branch
    git branch -d feat/add-image-watermarking
    # Delete personal remote branch
    git push origin --delete feat/add-image-watermarking
    # Delete company remote branch
    git push company --delete feat/add-image-watermarking
    ```

---

## Phase 3: Managing a Release

**Goal:** To create an official, versioned release of the project. This is typically done by the project administrator.

1.  **Ensure `main` is Synced:**
    ```bash
    git switch main
    git pull --rebase company main
    ```
2.  **Update the `release` Branch:**
    ```bash
    git switch release
    git pull --rebase company release
    git merge main
    git push company release
    ```
3.  **Create and Push the Signed Tag:**
    ```bash
    # The -s flag creates a GPG-signed tag. The -m is the annotation message.
    git tag -s v1.1.0 -m "Release v1.1.0: Adds caching and workflow guide"

    # Push the tag to both remotes
    git push company v1.1.0
    git push origin v1.1.0
    ```
4.  **Return to Development:**
    ```bash
    git switch main
    ```

---

## Development Best Practices & Naming Conventions

### 1. Branch Naming Convention

**Format:** `type/short-description` (e.g., `feat/add-image-watermarking`)
-   `feat`: A new feature.
-   `fix`: A bug fix.
-   `docs`: Changes to documentation.
-   `style`: Code style changes.
-   `refactor`: A code change that neither fixes a bug nor adds a feature.
-   `test`: Adding or correcting tests.
-   `chore`: Changes to the build process or auxiliary tools.

### 2. Commit Message Convention

We follow the **[Conventional Commits](https://www.conventionalcommits.org/)** standard.
**Format:** `<type>(<scope>): <subject>`
-   **Example:** `fix(gemini-client): Add guard clause to prevent auth crash`

### 3. Pull Request (PR) Convention

-   **Title:** Should be a clean, descriptive summary following the commit message convention.
-   **Description:** Briefly explain the "what" and "why" of the change. Include steps for how to test it.

---

## Git Command Cheat Sheet

| Task                               | Modern Command                                  |
| :--------------------------------- | :---------------------------------------------- |
| **Branching**                      |                                                 |
| See all local branches             | `git branch`                                    |
| Switch to an existing branch       | `git switch <branch-name>`                      |
| Create and switch to a new branch  | `git switch -c <branch-name>`                   |
| Delete a local branch (force)      | `git branch -D <branch-name>`                   |
| Delete a remote branch             | `git push <remote-name> --delete <branch-name>` |
| **Syncing**                        |                                                 |
| See your remotes                   | `git remote -v`                                 |
| Fetch latest from a remote         | `git fetch <remote-name>`                       |
| Pull (fetch + rebase) from remote  | `git pull --rebase <remote> <branch>`           |
| Rebase current branch onto another | `git rebase <branch-name>`                      |
| **Stashing**                       |                                                 |
| Save uncommitted work              | `git stash`                                     |
| See your list of stashes           | `git stash list`                                |
| Apply the most recent stash        | `git stash pop`                                 |