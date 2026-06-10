# ATS and recruiter-skim rules

A tailored resume has two first readers: an ATS parser and a recruiter's 6-second skim. Clear both before any human hiring manager sees it.

## ATS (applicant tracking system) parsing
- Single-column, linear layout. Multi-column layouts, sidebars, and text boxes get mangled or dropped by many parsers. The `templates/resume.html` template is single-column; keep it that way.
- Standard section headings: "Summary" or "About", "Work Experience", "Skills", "Education", and "Clearance" if relevant. Do not get clever with heading names; parsers match on them.
- No text inside images. All content as real text. A PDF rendered from HTML is fine; an image-only PDF is not.
- Keyword match to the JD. Parsers and recruiters search for the JD's exact terms. If the JD says "capability-based planning" and the candidate did that, use that phrase. Mirror the JD's vocabulary for the same real thing. Never claim a skill the candidate lacks.
- Spell out then abbreviate on first use for key terms when space allows, for example "User Acceptance Testing (UAT)".
- File naming: inside the packet folder the file is always `resume.pdf`; the pipeline depends on that name. If exporting a standalone copy outside the packet, name it `<Candidate Name> - <Role> - <Company>.pdf`.
- Dates in a consistent format the parser can read, for example "March 2020 to June 2024".

## Recruiter 6-second skim
- The headline equals the exact job title they are hiring for. Instant relevance signal.
- The top third does the work: the summary plus the most-recent role's first two or three bullets must contain the JD's core competencies and the biggest numbers.
- Numbers left-aligned and early in the bullet. A skimmer scans for digits.
- The strongest, most JD-relevant bullet goes first in each role.

## Keyword-coverage check (run at Step 4)
List the JD's must-have terms and skills. For each, mark it present-and-truthful, present-but-weak, absent-but-true (add it), or absent-and-false (do not add). Report the coverage. Aim to truthfully cover every must-have; never fabricate to fill a gap.

## What ATS optimization is NOT
- Not white-text keyword stuffing, which is flagged and dishonest.
- Not claiming JD skills the candidate does not have.
- Not cramming every keyword. Relevance and truth beat raw coverage count.
