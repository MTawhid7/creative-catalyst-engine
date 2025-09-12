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
2.  **Commit Your Changes** in small, logical units, following the [Commit Message Conventions](#commit-message-conventions).
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
3.  **Write a clear title and a detailed description.** Follow the [Pull Request Conventions](#pull-request-conventions).
4.  **Assign teammates as Reviewers.**

### Step 5: Handling the Code Review Conversation

**Goal:** Collaboratively refine your code based on team feedback.

-   **If they request changes:** Make the changes on your local feature branch, commit, and push to both `origin` (for backup) and `company` (to update the PR). The PR will automatically show your new commits.
-   **If you disagree with a suggestion:** Reply to the comment on GitHub. Respectfully explain your reasoning with evidence. The goal is a technical discussion to find the best solution.

### Step 6: Finalizing the Merge (Best Practice: Squash and Merge)

1.  **Merge the PR using "Squash and Merge":** Once the Pull Request is approved, click the **dropdown arrow** on the green merge button. Select **"Squash and merge"**.
2.  **Edit the Commit Message:** Condense the automatically generated list of commits into a single, clear message that follows our [Commit Message Conventions](#commit-message-conventions).
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

<a name="2-commit-message-convention"></a>
## 2. Commit Message Conventions

**Purpose:** Ensure commit messages are consistent, discoverable, and helpful in changelogs.

**Format (Conventional Commits style):**


---

## Phase 3: Development Best Practices (The "Why")

This workflow is designed to optimize for clarity, safety, and a clean history. Adhering to these principles will make you a more efficient and effective developer.

### Best Practices (The "Why")

*   **Commit Early, Commit Often, Push to `origin` Constantly:** Treat `git push origin <your-branch>` as your "save" button.
*   **Keep `main` Pristine:** Your local `main` branch should always be a perfect, clean mirror of the official `company/main`.
*   **Prefer Rebase Over Merge:** Always use `git pull --rebase` and `git rebase company/main` on your feature branches to create a clean, linear history.
*   **Keep Pull Requests Small and Focused:** A PR should do one thing and do it well. Small PRs get reviewed faster and are safer to integrate.

### Branch Naming Conventions

**Format:** `type/short-description` (e.g., `feat/add-image-watermarking`)
-   `feat`: A new feature.
-   `fix`: A bug fix.
-   `docs`: Changes to documentation.
-   `style`: Code style changes.
-   `refactor`: A code change that neither fixes a bug nor adds a feature.
-   `test`: Adding or correcting tests.
-   `chore`: Changes to the build process or auxiliary tools.

### Commit Message Conventions

We follow the **[Conventional Commits](https://www.conventionalcommits.org/)** standard.
**Format:** `<type>(<scope>): <subject>`
-   **Example:** `fix(gemini-client): Add guard clause to prevent auth crash`

### Pull Request Conventions

-   **Title:** Should be a clean, descriptive summary following the commit message convention.
-   **Description:** Briefly explain the "what" and "why" of the change. Include steps for how to test it.


---

## Phase 4: Scenarios & Recovery (The "Oh No!" Guide)

Mistakes happen. The true measure of a developer is not avoiding mistakes, but knowing how to recover from them cleanly. This section covers the most common scenarios.

### Scenario 1: "I made a typo in my last commit message" or "I forgot to add a file."

This is the most common issue and the easiest to fix. As long as you have not pushed the commit to the `company` remote, you can use `amend`.

1.  **Stage the forgotten file (if any):**
    ```bash
    git add path/to/forgotten-file.py
    ```
2.  **Amend the previous commit:**
    ```bash
    # The --no-edit flag will keep the same commit message
    git commit --amend --no-edit

    # Or, to edit the message at the same time:
    git commit --amend
    ```
3.  **Force-push to your personal remote** to update your backup:
    ```bash
    git push --force-with-lease origin feat/my-branch
    ```

### Scenario 2: "My branch has messy 'wip' and 'fixup' commits that I want to clean up before my PR."

This is the perfect use case for an **interactive rebase**. It is your most powerful tool for creating a clean, professional history.

1.  **Start the interactive rebase:**
    ```bash
    # This will open an editor with a list of all the commits on your branch
    # that are not yet in the official company/main.
    git rebase -i company/main
    ```
2.  **Edit the commit list:** Your editor will show a list of your commits, each prefixed with the word `pick`. To clean up your history, change `pick` to one of the following commands (the most common are `s` and `f`):
    *   `reword` or `r`: Keep the commit, but change its message.
    *   `squash` or `s`: Combine this commit's changes *and* its message into the commit above it.
    *   `fixup` or `f`: Combine this commit's changes into the commit above it, but **discard** this commit's message entirely. This is perfect for "fixup" commits.

    **Example:**
    ```
    # Before
    pick a1b2c3d feat: Implement the core function
    pick d4e5f6g fixup: Add forgotten comment
    pick h7i8j9k wip: Trying something out

    # After (to combine the 'fixup' and 'wip' into the first commit)
    pick a1b2c3d feat: Implement the core function
    f d4e5f6g fixup: Add forgotten comment
    s h7i8j9k wip: Trying something out
    ```
3.  **Save and close the editor.** Git will now apply your changes. If you used `squash` or `reword`, another editor will open to let you combine the commit messages.

### Scenario 3: "I started a rebase, and now I have a huge, terrifying merge conflict."

This can be stressful, but Git gives you a powerful escape hatch.

*   **The Escape Hatch (Safest Option):** If you are overwhelmed, you can always abort the rebase and return your branch to the state it was in before you started.
    ```bash
    git rebase --abort
    ```
*   **The Professional Way (Resolving the Conflict):**
    1.  Run `git status`. It will tell you which files have conflicts.
    2.  Open each conflicted file. Your editor (like VS Code) will have excellent built-in tools to show you the "incoming" change and your "current" change.
    3.  Edit the file to resolve the conflict, removing the `<<<<<<<`, `=======`, and `>>>>>>>` markers.
    4.  Once you have fixed a file, stage it: `git add path/to/resolved-file.py`.
    5.  When all conflicts are resolved and staged, continue the rebase:
        ```bash
        git rebase --continue
        ```

### Scenario 4: "I accidentally committed directly to my `main` branch."

1.  **First, get your work onto a new branch.** This ensures your changes are safe.
    ```bash
    # Make sure you are on the main branch
    git switch main

    # Create a new branch from the current (bad) state of main
    git switch -c feat/my-saved-work
    ```
2.  **Now, reset your `main` branch back to the official version.**
    ```bash
    git switch main

    # This will discard all local changes on 'main' and make it a perfect
    # mirror of the company's main branch.
    # WARNING: This is a destructive command. Only run it on 'main'.
    git reset --hard company/main
    ```
3.  You are now safe. Your `main` branch is clean, and your work is safe on the `feat/my-saved-work` branch.

---

## Strategic Command Reference

| Command                          | Use Case / When to Use It                                                                                       |
| :------------------------------- | :-------------------------------------------------------------------------------------------------------------- |
| **Daily Workflow**               |                                                                                                                 |
| `git switch -c <branch>`         | At the start of a new task, to create a clean branch based on the latest `main`.                                |
| `git commit -m "..."`            | After completing a small, logical unit of work.                                                                 |
| `git push origin <branch>`       | Frequently throughout the day. Treat it like saving your work.                                                  |
| `git pull --rebase company main` | On your `main` branch to sync it. On your feature branch to update it.                                          |
| **History Management**           |                                                                                                                 |
| `git commit --amend`             | When you need to fix a typo or add a file to your *most recent* commit.                                         |
| `git rebase -i company/main`     | Before opening a Pull Request, to clean up your messy commit history into a few clear, logical commits.         |
| `git push --force-with-lease`    | After amending or rebasing a branch that has already been pushed to your personal remote (`origin`).            |
| **Recovery & Safety**            |                                                                                                                 |
| `git stash`                      | When you need to quickly switch branches but have uncommitted work you don't want to lose.                      |
| `git rebase --abort`             | Your escape hatch. Use it to safely exit a rebase that has gone wrong (e.g., a major conflict).                 |
| `git reset --hard <commit>`      | A powerful but destructive tool. Primarily used to reset your local `main` branch to match the official remote. |