# Your workspace

This repo holds the code, skills, and templates. Your personal job-search data lives somewhere else:
a workspace folder you choose during setup (default `~/job-search`). Keeping the two separate means you
can update the repo without touching your data, and your data never risks getting committed.

The setup skill asks where you want the workspace and creates this structure:

```
<workspace_root>/                e.g. ~/job-search
  about-me.md                    your accomplishment bank: every accomplishment, tagged,
                                 in did-X / resulting-in-Y / outcome-Z form. The single source
                                 of truth the resume and cover-letter skills select from.
  profile.md                     who you are and what you want (titles, industries, geos,
                                 constraints, positioning). Steers matching and tone.
  master-resume.html             your base resume, styled from templates/resume.html and filled
                                 from about-me.md. The starting point each tailored resume edits.
  jobs.csv                       the tracker sheet, if you use the CSV backend. (Google Sheets
                                 users keep this in the cloud instead.)
  applications/
    <Company> - <Role>/          one folder per job you marked "Yes"
      jd.md                      the saved job description
      resume.md                  tailored resume draft
      cover-letter.md            tailored cover letter draft
      application-questions.md   answers to the posting's substantive questions
      resume.html                styled resume, rendered from the template
      cover-letter.html          styled cover letter, rendered from the template
      resume.pdf                 PDF, rendered by the scheduler when Chrome is available
      cover-letter.pdf           PDF, same deal
```

The config keys `workspace_root`, `accomplishment_bank`, `profile_file`, `applications_dir`, and
`csv_path` point at this folder. Change `workspace_root` and re-point the others if you move it.

Why "about-me.md" and not "resume.md": your resume is a tailored, trimmed view for one job. about-me.md
is the full superset of everything you have done, with the numbers, that the agent draws from to build
each tailored resume and cover letter. You grow about-me.md over time; the agent never invents beyond it.

Search settings (your company list and match terms) stay in the repo at `config/companies.txt` and
`config/terms.md`, because they are configuration rather than personal history. Starter company lists for
common industries are in `config/seed-companies/`.
