# The Creative Catalyst Engine: Professional Git Workflow Guide

Welcome to the official development workflow for this project. This guide is the single source of truth for how we write, review, and submit code. Following these steps ensures our project history remains clean, our code stays stable, and our collaboration is efficient and safe.

### The Golden Rule: The Workshop vs. The Showroom

To understand this workflow, you only need to remember one core concept:

-   **Your Personal Repo (`origin`):** This is your **Workshop**. It's your private, safe space to experiment, make messes, and save your daily progress. Pushing here is frequent and informal.
-   **The Company Repo (`company`):** This is the **Official Showroom**. It is the single source of truth for the project. Code only enters the showroom after it is complete, tested, and formally approved by the team via a Pull Request.

### Key Branches & Their Purpose

-   **`feature` branches (e.g., `feat/add-new-model`):** Temporary "drafts" where all new work happens. They are created locally and deleted after being merged.
-   **`main` branch:** The primary integration branch. It represents the latest, stable, development-ready version of the project. **Direct pushes to this branch are forbidden by process.**
-   **`release` branch:** A highly stable branch that represents the "shippable" or "production-ready" version of the code.

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
    # The name 'origin' will now point to your personal repo
    git remote add origin <your-personal-repo-url>
    ```

3.  **Rename the Original Remote to `company`:**
    ```bash
    # The default remote name is 'origin', we rename it to be more descriptive
    git remote rename origin company
    ```

4.  **Verify Your Remotes:**
    ```bash
    git remote -v
    ```
    *You should see both `company` and `origin` listed.*

5.  **Set the Upstream for Your `main` Branch:** This is a critical step that tells `git status` to compare your local `main` against the company's `main`, which is our source of truth.
    ```bash
    git checkout main
    git branch --set-upstream-to=company/main
    ```

---

## Phase 2: The Core Workflow Cycle

This is the end-to-end process for taking a task from idea to completion.

### Step 1: Start of Day / Start of New Task

**Goal:** Sync your local machine with the official project before writing any code.

1.  **Switch to your local `main` branch.**
    ```bash
    git checkout main
    ```
2.  **Pull the latest official code from the `company` remote.** This downloads any changes your collaborators have merged and updates your local `main` to match.
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
2.  **Commit Your Changes** in small, logical units.
    ```bash
    git add .
    git commit -m "feat: Implement the core watermarking function"
    ```
3.  **Push to Your Personal Repo (`origin`)**. This is your backup. The company repo is not affected.
    ```bash
    # For the first time pushing a new branch:
    git push -u origin feat/add-image-watermarking
    # For all subsequent pushes on this branch:
    git push origin
    ```

### Step 3: Keeping Your Branch Synced (Rebasing)

**Goal:** Keep your feature branch updated with the latest changes from the official `main` branch, preventing difficult merges later.

**Scenario:** A teammate has just merged a big feature into the company's `main` branch.

1.  **Fetch the latest history from the `company` remote.** This downloads all new commits but doesn't change your code yet.
    ```bash
    git fetch company
    ```
2.  **Rebase your branch onto the official `main`.** This rewrites your branch's history to be a clean, straight line starting from the latest official code.
    ```bash
    # Make sure you are on your feature branch
    git rebase company/main
    ```
3.  **Force-push the updated branch to your personal remote.** Because `rebase` rewrites history, you must force-push. This is safe because it's your own branch in your personal "Workshop."
    ```bash
    git push --force-with-lease origin feat/add-image-watermarking
    ```

### Step 4: Submitting Your Work for Review (The Pull Request)

**Goal:** Formally propose your completed feature for inclusion in the official project.

1.  **Open a Pull Request (PR) on the Company's GitHub Repo.**
    -   Go to the company repository on GitHub.
    -   Click the **"Pull requests"** tab, then click the green **"New pull request"** button.
    -   You will see a screen comparing branches *within* the company repo. **This is not what you want.** Look for a small blue link that says **"compare across forks"**. Click it.
2.  **Configure the branches manually.** You will now see four dropdown menus. Set them as follows:
    -   **`base repository`**: `technyxai/CreativeCatalystEngine`
    -   **`base`**: `main` (The destination)
    -   **`head repository`**: `MTawhid7/creative-catalyst-engine` (Your personal repo)
    -   **`compare`**: `feat/add-image-watermarking` (The source)
3.  **Write a clear title and a detailed description.** Explain what you did and why.
4.  **Assign your teammates as Reviewers.**

### Step 5: Handling the Code Review Conversation

**Goal:** Collaboratively refine your code based on team feedback.

-   **If they request changes:**
    1.  On your local machine, switch to your feature branch (`git checkout feat/add-image-watermarking`).
    2.  Make the requested code changes.
    3.  Commit and `git push origin`. The Pull Request will automatically update.
    4.  Comment on GitHub to let them know you've addressed the feedback.

-   **If you disagree with a suggestion:**
    1.  Do not ignore it. Reply to the comment on GitHub.
    2.  Respectfully explain your reasoning with evidence (e.g., performance, architecture, bug prevention).
    3.  The goal is a technical discussion to find the best solution for the project.

### Step 6: Finalizing the Merge

**Goal:** Officially add your feature to the project.

1.  **Merge the PR:** Once approved, an admin (you or a collaborator) will click the green **"Merge pull request"** button on GitHub. Your code is now in the company's `main` branch.

### Step 7: The "Sync Back" and Cleanup

**Goal:** Update your personal repository to reflect the new state of the official project.

1.  **Update your local `main` branch.**
    ```bash
    git checkout main
    git pull company main
    ```
2.  **Update your personal remote's `main` branch.** This is the final sync.
    ```bash
    git push origin main
    ```
3.  **Clean up your branches.**
    -   GitHub will give you a button to delete the remote feature branch after merging. Use it.
    -   Delete your local feature branch:
        ```bash
        git branch -d feat/add-image-watermarking
        ```

---

## Special Scenarios & Advanced Usage

### Handling Experiments: `git stash`

-   **Save uncommitted work for later:** `git stash`
-   **See your list of stashes:** `git stash list`
-   **Apply the most recent stash:** `git stash pop`
-   **Delete all stashes:** `git stash clear`

### Handling Merge Conflicts During a Rebase

If you `rebase` and Git finds a conflict, it will pause and tell you which file is conflicted.

1.  **Open the conflicted file.** You will see markers:
    ```
    <<<<<<< HEAD
    // Your changes
    =======
    // The incoming changes from main
    >>>>>>> <commit-hash>
    ```
2.  **Edit the file manually.** Delete the markers and decide which code to keep (yours, theirs, or a combination of both).
3.  **Stage the fixed file.**
    ```bash
    git add path/to/the/fixed/file.py
    ```
4.  **Continue the rebase.**
    ```bash
    git rebase --continue
    ```
5.  If you get stuck, you can always safely abort the rebase and return to where you started: `git rebase --abort`.

### Undoing Mistakes

-   **Amend your last commit (if you haven't pushed yet):**
    ```bash
    # Make your changes
    git add .
    git commit --amend --no-edit
    ```
-   **Revert a commit that has already been pushed:** This creates a *new* commit that undoes a previous one. It's the safest way to undo public changes.
    ```bash
    # Find the hash of the commit you want to revert
    git log
    # Create the revert commit
    git revert <commit-hash>
    ```