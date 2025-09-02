# The Definitive Git Workflow Guide

Welcome to the official development workflow for the Creative Catalyst Engine. This guide is the single source of truth for how we write, review, and submit code. Following these steps ensures our project history remains clean, our code stays stable, and our collaboration is efficient and safe.

### The Golden Rule: The Workshop vs. The Showroom

To understand this workflow, you only need to remember one core concept:

-   **Your Personal Repo (`origin`):** This is your **Workshop**. It's your private, safe space to experiment, make messes, and save your daily progress. Pushing here is frequent and informal.
-   **The Company Repo (`company`):** This is the **Official Showroom**. It is the single source of truth for the project. Code only enters the showroom after it is complete, tested, and formally approved by the team via a Pull Request.

### Key Branches & Their Purpose

-   **`feature` branches (e.g., `feat/add-new-model`):** Temporary "drafts" where all new work happens. They are created locally and deleted after being merged.
-   **`main` branch:** The primary integration branch. It represents the latest, stable, development-ready version of the project. **Direct pushes to this branch are forbidden by process.**
-   **`release` branch:** A highly stable branch that is a "snapshot" of `main` at a specific point in time. It represents the "shippable" or "production-ready" version of the code.

---

## Phase 1: The One-Time Setup

**Goal:** Configure your local machine to correctly interact with both repositories. You only need to do this once.

1.  **Clone the Company Repository:**
    ```bash
    git clone <company-repo-url> CreativeCatalystEngine
    cd CreativeCatalystEngine
    ```

2.  **Add Your Personal Repo as a Remote:**
    ```bash
    git remote add origin <your-personal-repo-url>
    ```

3.  **Rename the Original Remote to `company`:**
    ```bash
    git remote rename origin company
    ```

4.  **Verify Your Remotes:** `git remote -v` (You should see both `company` and `origin` listed).

5.  **Set the Upstream for Your `main` Branch:** This critical step tells `git status` to compare your local `main` against the company's `main`.
    ```bash
    git checkout main
    git branch --set-upstream-to=company/main
    ```

---

## Phase 2: The Core Feature Workflow Cycle

This is the end-to-end process for taking a task from idea to completion.

### Step 1: Start of Day / Start of New Task

**Goal:** Sync your local machine with the official project before writing any code.

1.  **Switch to your local `main` branch.**
    ```bash
    git checkout main
    ```
2.  **Pull the latest official code from the `company` remote.**
    ```bash
    git pull company main
    ```
3.  **Create your feature branch.** This creates a safe, isolated sandbox for your work.
    ```bash
    git checkout -b feat/add-image-watermarking
    ```

### Step 2: Daily Development (The "Code, Commit, Push" Loop)

**Goal:** Write code and safely back it up to your personal "Workshop" repo.

1.  **Write and Test Your Code** on your feature branch.
2.  **Commit Your Changes** in small, logical units with clear messages.
    ```bash
    git add .
    git commit -m "feat: Implement the core watermarking function"
    ```
3.  **Push to Your Personal Repo (`origin`)**. This is your backup. The company repo is not affected.
    ```bash
    git push -u origin feat/add-image-watermarking
    ```

### Step 3: Keeping Your Branch Synced (Rebasing)

**Goal:** Keep your feature branch updated with the latest changes from the official `main` branch to maintain a clean history.

1.  **Fetch the latest history from the `company` remote.**
    ```bash
    git fetch company
    ```
2.  **Rebase your branch onto the official `main`.** This replays your work on top of the latest code.
    ```bash
    git rebase company/main
    ```
3.  **Force-push the updated branch to your personal remote.** This is required and safe after rebasing a feature branch.
    ```bash
    git push --force-with-lease origin feat/add-image-watermarking
    ```

### Step 4: Submitting Your Work for Review (The Pull Request)

**Goal:** Formally propose your completed feature for inclusion in the official project.

1.  **Push your feature branch to the `company` remote.** This is the "bridge" step that makes your work visible inside the company project.
    ```bash
    git push company feat/add-image-watermarking
    ```
2.  **Open a Pull Request (PR) on the Company's GitHub Repo.** A banner for your recently pushed branch will automatically appear. Click **"Compare & pull request"**.
3.  **Write a clear title and a detailed description.** Explain what you did and why.
4.  **Assign your teammates as Reviewers.**

### Step 5: Handling the Code Review Conversation

**Goal:** Collaboratively refine your code based on team feedback.

-   **If they request changes:** Make the changes on your local feature branch, commit, and push to both `origin` and `company`. The PR will automatically update.
-   **If you disagree with a suggestion:** Reply to the comment on GitHub. Respectfully explain your reasoning with evidence. The goal is a technical discussion to find the best solution.

### Step 6: Finalizing the Merge (Best Practice: Squash and Merge)

**Goal:** Officially add your feature to the project with a clean, linear history.

1.  **Merge the PR using "Squash and Merge":** Once the Pull Request is approved, click the **dropdown arrow** on the green merge button. Select **"Squash and merge"**.
2.  **Edit the Commit Message:** Condense the automatically generated list of commits into a single, clear message that summarizes the feature (e.g., "feat: Add multi-model image generation support").
3.  **Confirm the merge.** Your feature is now represented by a single, clean commit on the `main` branch.

### Step 7: The "Sync Back" and Final Cleanup

**Goal:** To reset your entire workspace to a clean state after your feature has been officially merged.

1.  **Update your local `main` branch.**
    ```bash
    git checkout main
    git pull company main
    ```
2.  **Update your personal remote's `main` branch.**
    ```bash
    git push origin main
    ```
3.  **Delete the feature branch from all locations.**
    ```bash
    git branch -d feat/add-image-watermarking
    git push origin --delete feat/add-image-watermarking
    git push company --delete feat/add-image-watermarking
    ```

---

## Phase 3: Managing a Release

**Goal:** To update the stable `release` branch with the latest approved features from `main`.

### When to Update the `release` Branch

This is not a daily task. You should update the `release` branch only when `main` has accumulated enough new, stable features to constitute a new "version" of the project, or before a planned deployment.

### The Release Update Workflow

1.  **Ensure your local `main` is fully synced** with the company's `main`.
    ```bash
    git checkout main
    git pull company main
    ```
2.  **Switch to your local `release` branch.**
    ```bash
    git checkout release
    ```
3.  **Pull the latest `release` from the company repo.** This is a critical safety check to ensure you have any hotfixes that may have been applied.
    ```bash
    git pull company release
    ```
4.  **Merge `main` into `release`.** This brings all the new, approved features into your release candidate.
    ```bash
    git merge main
    ```
5.  **Push the updated `release` branch to the company repo.** This makes the new release official.
    ```bash
    git push company release
    ```
6.  **Switch back to `main`** to continue development work.
    ```bash
    git checkout main
    ```

---

## Special Scenarios & Best Practices

### Best Practices for Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) standard. This makes the history easy to read.
-   `feat:` A new feature. (e.g., `feat: Add image watermarking`)
-   `fix:` A bug fix. (e.g., `fix: Correct Gemini client initialization`)
-   `docs:` Changes to documentation. (e.g., `docs: Update workflow guide`)
-   `style:` Code style changes (formatting, etc).
-   `refactor:` A code change that neither fixes a bug nor adds a feature.
-   `chore:` Changes to the build process or auxiliary tools.

### Handling Experiments: `git stash`

-   **Save uncommitted work for later:** `git stash`
-   **See your list of stashes:** `git stash list`
-   **Apply the most recent stash:** `git stash pop`

### Undoing Mistakes

-   **Amend your last commit (if you haven't pushed yet):**
    ```bash
    git add .
    git commit --amend --no-edit
    ```
-   **Revert a pushed commit:** This creates a *new* commit that undoes a previous one.
    ```bash
    git revert <commit-hash>
    ```