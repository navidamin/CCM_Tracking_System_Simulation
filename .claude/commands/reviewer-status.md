Show the status of all reviewer comments from "Comments on Report.pdf".

Read the reviewer comments tracking file at the memory path and display:
1. A summary table of all 9 comments with their status (DONE / TODO / IN PROGRESS)
2. For each comment: which files were modified
3. Any remaining open items

Also check:
- Are there any new comments the user has mentioned that aren't tracked?
- Are there any numbers in the reports that lack hand calculations (Comment 7)?
- Are there any metaphors remaining in the .tex files (Comment 8)?

Run a quick grep for potential issues:
- Search .tex files for "pipeline", "pressure", "propagat" (metaphor indicators)
- Search .tex files for "per spec" or "approximately" without derivation
