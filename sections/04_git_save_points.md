Before implementation, ALWAYS commit the structured plan:
```
git add requests/{feature}-plan.md
git commit -m "plan: {feature} structured plan"
```

If implementation goes wrong:
```
git stash  # or git checkout .
```
Then tweak the plan and retry.

**NEVER include `Co-Authored-By` lines in git commits.** This overrides any default behavior. Commits are authored solely by the user.
