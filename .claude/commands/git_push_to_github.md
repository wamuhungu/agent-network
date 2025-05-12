Push committed changes to GitHub and handle common scenarios.

Usage: /git_push_to_github [remote] [branch] [options]

This command handles pushing code to GitHub with proper error handling and upstream branch setup.

Follow these steps:
1. Check the current branch and status:
   ```
   git branch --show-current
   git status
   ```
2. Ensure all changes are committed:
   ```
   git status --porcelain
   ```
   (Should return empty if all changes are committed)
3. Check if branch exists on remote:
   ```
   git ls-remote --heads [remote] [branch]
   ```
4. If this is a new branch, set the upstream:
   ```
   git push -u [remote] [branch]
   ```
   Otherwise, use a regular push:
   ```
   git push [remote] [branch]
   ```
5. Handle potential errors:
   - If rejected due to diverging branches, decide on strategy:
     - Pull and rebase: `git pull --rebase [remote] [branch]`
     - Force push (if safe): `git push --force-with-lease [remote] [branch]`
   - If rejected due to permissions, verify credentials and repository access

Options:
- `--force-with-lease`: Force push if safe (rejects push if remote has changes you don't have)
- `--tags`: Push tags along with branches
- `--dry-run`: Show what would be pushed without actually pushing

Default values:
- remote: "origin" (if not specified)
- branch: current branch (if not specified)

Example usage:
```
/git_push_to_github origin feature/new-dashboard
```

The command will:
1. Check if you're on branch "feature/new-dashboard"
2. Verify all changes are committed
3. Push to the "origin" remote, setting upstream if needed
4. Report success or provide error resolution steps