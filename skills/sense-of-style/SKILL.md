---
name: sense-of-style
description: Diagnose and rewrite prose using Steven Pinker's Sense of Style principles plus an AI-writing-tells check. Scores writing on 9 style dimensions, flags specific line-level problems (nominalizations, passive voice, hedges, broken topic chains, cliches, AI tells), and produces a rewrite. Use on any prose document (resumes, cover letters, application answers, posts, emails) when the content is right but the writing is soft. Trigger phrases include "run sense-of-style", "style pass", "tighten the prose", "Pinker this", "/sense-of-style".
version: 1.0.0
allowed-tools: [Read, Write, Edit, Glob, Grep, AskUserQuestion]
---

> Voice: read `config/profile.md` for the candidate's voice and tone. This skill enforces Pinker's style principles on top of that voice; they should align, not conflict.
>
> AI-writing tells: before the diagnostic pass, scan the draft against the full catalog of AI-writing tells described in dimension 9 below. Strip any tell on rewrite unless it is genuinely the best tool for that exact sentence. This is a hard rewrite rule. The candidate's writing must never read as machine-generated.

# Sense of Style : Prose Diagnostic and Rewrite

A style-focused quality pass grounded in Steven Pinker's *The Sense of Style*. Scores prose on 9 dimensions, flags line-level problems with concrete fixes, and produces a rewrite that preserves voice while killing the things that make writing soft.

## When to Use

Activate when:
- The user says "run sense-of-style", "style pass", "tighten the prose", "Pinker this".
- Content is right but the writing feels bloated, academic, or soft.
- As a polish pass after the argument is already sound.
- The user invokes `/sense-of-style` with or without a file path.
- A resume, cover letter, or application answer is finalized and needs at least one style pass before it ships.

Do NOT use for:
- First drafts (generate content first).
- Pure content or argument problems.
- Code review (prose only).

---

## The 9 Scoring Dimensions

Each dimension scored 1 to 10. Target: all at 8 of 10 or higher.

### 1. Classic Style
Writer and reader are equals looking at something concrete in the world. No throat-clearing, no "in this document I will argue", no meta-commentary.

9/10: "The auth middleware stores session tokens in plaintext. Legal flagged this in Q3."
3/10: "It is important to note that in this section we will be discussing certain concerns that have been raised regarding authentication."

### 2. Curse of Knowledge
The reader does not know what you know. Jargon gets defined, abstractions get examples, references get context.

Flags: unexplained acronyms, insider shorthand, abstract concepts without grounding examples, assumptions about the reader's mental model.

### 3. Concreteness (Verbs and Nouns)
Nouns should be things you can point at. Verbs should be actions. Kill nominalizations.

Common fixes:
- "make a decision" to "decide"
- "provide clarification" to "clarify"
- "the implementation of" to "implementing", or just "we built"
- "utilization of the framework" to "using the framework"

### 4. Active Voice and Named Agents
Default to active. Name who is doing what. Passive is legitimate only when the patient is the topic or the agent is unknown or irrelevant.

Flags: "it was decided that", "mistakes were made", agentless passives, abstract subjects doing abstract things.

### 5. Given-Before-New (Topic Chains)
Each sentence starts with what the reader already knows and ends with new information. Broken topic chains mean the reader feels lost without knowing why.

Flags: paragraphs where each sentence introduces a fresh subject, missing connective tissue, jumps that require the reader to reconstruct the link.

### 6. Syntax Load and Rhythm
Shallow syntax trees. Heavy phrases at the end, not the front. Vary sentence length. Short sentences land. Long sentences explain.

Flags: heavy left-branching, garden-path sentences, stacks of prepositional phrases, uniform sentence length across a paragraph.

### 7. Word Economy
Every word earns its place. Cut hedges, metadiscourse, and filler.

Cut list:
- Hedges: "somewhat", "rather", "arguably", "in some sense", "kind of".
- Intensifiers that weaken: "very", "really", "quite", "basically", "actually", "just".
- Metadiscourse: "it is important to note", "as mentioned above", "in this section".
- Bloat: "in order to" to "to"; "due to the fact that" to "because"; "at this point in time" to "now".

### 8. Freshness (No Cliches, No Bureaucratese)
Dead language signals dead thinking. Stock phrases get replaced with the specific thing you actually mean.

Flags: "at the end of the day", "move the needle", "unlock value", "leverage synergies", "best-in-class", "going forward", "circle back", "touch base".

### 9. No AI-Writing Tells
Writing must not read as machine-generated. Scan against the full catalog:
- Vocabulary: delve, tapestry, leverage, robust, seamless, pivotal, and similar.
- Sentence templates: negative parallelism ("it's not X, it's Y" and its mutation "you're not just X, you're Y"); tricolons; "here's the thing" or "the result?" reveals; copula-avoidance ("serves as", "stands as a testament").
- Participial significance tails (", underscoring its importance").
- Stock phrases ("it's worth noting", "in today's fast-paced world", "in conclusion").
- Sycophancy and chat-closers ("great question", "would you like me to").
- Punctuation and formatting tells: em-dash overuse, bold lead-in bullets, emoji markers, curly quotes, invisible Unicode.
- Structural habits: both-sides hedging, strategic vagueness, uniform sentence length, aphoristic kickers, promotional register.

Single words are weak signals; the giveaway is density and clustering. Score down for any cluster, flag every instance, and strip on rewrite unless one is genuinely the best tool for that exact sentence. The durable fixes: take a stance, get specific (names, numbers, dates), vary rhythm, cut rhetorical devices to near zero.

9/10: "It runs on-prem so sensitive data never leaves the building. That's the whole pitch."
2/10: "In today's rapidly evolving landscape, it isn't just a workspace, it's a testament to secure innovation, seamlessly empowering teams to navigate the complexities of compliance."

---

## Workflow

1. Load the document (file path or inline content).
2. Diagnostic pass: line-level flags with specific problems.
3. Score all 9 dimensions with evidence quotes.
4. Ask the user: diagnostic only, full rewrite, or section-by-section. In a headless run, default to full rewrite.
5. Rewrite (if requested) preserving voice.
6. Re-score and output a changelog.

---

## Step 1: Load Document

File mode: `/sense-of-style /path/to/draft.md`
Inline mode: `/sense-of-style` (operates on the most recently written or edited content in the conversation)

If the document is over 3000 words, ask whether to process the whole doc or a specific section.

---

## Step 2: Diagnostic Pass

Scan the document and flag concrete line-level problems. Output as a table, grouped by dimension. Every flag must quote the actual text and propose a specific fix.

Output format:

```markdown
## Diagnostic Flags

### Nominalizations (Concreteness)
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "The implementation of the new framework..." | Zombie noun "implementation" | "We built the new framework..." |
| "Utilization of the tool has increased" | "Utilization" hiding the verb | "More people use the tool" |

### Passive Voice (Active Voice)
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "It was decided that we would ship Friday" | Agentless passive | "Leadership decided to ship Friday" |

### Hedges & Metadiscourse (Word Economy)
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "It is important to note that users..." | Pure metadiscourse | [delete, say it directly] |
| "This is arguably somewhat concerning" | Double hedge | "This is a problem" |

### Cliches & Bureaucratese (Freshness)
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "We need to move the needle on engagement" | Cliche | "Engagement is flat at 12%, we need it above 25%" |

### Curse of Knowledge
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "The LTV:CAC ratio is underwater" | Unexplained jargon for a mixed audience | Define on first use or replace |

### Broken Topic Chains (Given-Before-New)
| Paragraph | Problem | Fix |
|-----------|---------|-----|
| Para 3 | Each sentence introduces a new subject; the reader has to reconstruct the connection | Reorder so each sentence picks up the previous sentence's topic |

### Syntax Load
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| [long heavy sentence] | 4 prepositional phrases stacked | Break into two sentences, move the heavy phrase to the end |

### Classic Style Violations
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "In this document we will examine..." | Throat-clearing | Delete; start with the substance |

### AI-Writing Tells (No AI-Writing Tells)
| Line/Quote | Problem | Fix |
|------------|---------|-----|
| "This isn't just a tool, it's a revolution." | Negative parallelism (top AI tell) | "This tool cuts onboarding from days to an hour." |
| "...empowering teams to navigate the complexities of compliance" | Stacked tell vocab (empower, navigate, complexities) | "...so the compliance team stops chasing sign-offs" |
| "It's worth noting that results may vary." | Hedge plus vagueness | Delete or commit: "Results held for teams under 50." |
| "- **Scalable**: handles growth" | Bold lead-in bullet | "Scales past 10k users without re-architecting." |
| "Fast. Simple. Effective." | Tricolon | Pick the one true claim and prove it |
```

If a dimension has zero flags, mark it clean and skip the section.

---

## Step 3: Score

Score each of the 9 dimensions 1 to 10, with a one-line rationale and one representative quote.

Output:

```markdown
## Style Scores

| # | Dimension | Score | Evidence |
|---|-----------|-------|----------|
| 1 | Classic Style | X/10 | "[quote]" : [why this score] |
| 2 | Curse of Knowledge | X/10 | "[quote]" : [why this score] |
| 3 | Concreteness | X/10 | "[quote]" : [why this score] |
| 4 | Active Voice | X/10 | "[quote]" : [why this score] |
| 5 | Given-Before-New | X/10 | "[paragraph ref]" : [why this score] |
| 6 | Syntax Load | X/10 | "[quote]" : [why this score] |
| 7 | Word Economy | X/10 | "[quote]" : [why this score] |
| 8 | Freshness | X/10 | "[quote]" : [why this score] |
| 9 | No AI-Writing Tells | X/10 | "[quote]" : [which tells, how dense] |

Overall: [sum]/90 ([percent])
Weakest dimensions: [top 3 to target]
```

---

## Step 4: Ask User How to Proceed

```yaml
questions:
  - question: "Diagnostic is complete. How do you want to proceed?"
    header: "Next Step"
    multiSelect: false
    options:
      - label: "Full rewrite"
        description: "Rewrite the whole document fixing all flagged problems"
      - label: "Section-by-section"
        description: "Walk through sections; I approve each rewrite"
      - label: "Diagnostic only"
        description: "Just the flags and scores; I'll rewrite myself"
      - label: "Target weakest dimensions"
        description: "Only rewrite sentences flagged on the 3 lowest-scoring dimensions"
```

In a headless run with no human, default to a full rewrite.

---

## Step 5: Rewrite

Rules for rewriting:

1. Preserve the author's voice. If the draft is direct, the rewrite is direct. Pinker's principles serve voice, they do not replace it.
2. Fix flagged problems only. Do not rewrite clean sentences. Do not add content. Do not change the argument.
3. Tighten aggressively. Expect 15 to 30 percent word reduction.
4. Preserve specificity. Numbers, names, dates, and quotes stay exact.
5. One idea per sentence. Break up stacked clauses when they exceed working-memory capacity.
6. Strip AI-writing tells (hard rule). Kill em-dash overuse, negative parallelism, tricolons, bold lead-in bullets, emoji markers, hedge phrases, and the tell-vocabulary cluster. Keep one only when it is genuinely the best tool for that exact sentence. When in doubt, cut it and get specific instead.

Output format:

```markdown
## Rewrite

### Changes Summary
- Cut X words ([percentage] reduction)
- Fixed [N] nominalizations, [N] passives, [N] hedges, [N] cliches
- Restructured [N] paragraphs for topic-chain coherence

### Side-by-Side (Notable Changes)

Change 1: [dimension]
- Before: "[original]"
- After: "[rewrite]"

Change 2: [dimension]
- Before: "[original]"
- After: "[rewrite]"

[show 5 to 10 representative changes, not every edit]

### Full Rewritten Document

[full rewrite]
```

---

## Step 6: Re-Score

Run scoring again on the rewrite. Output the score progression:

```markdown
## Score Progression

| Dimension | Before | After | Change |
|-----------|--------|-------|--------|
| Classic Style | X/10 | X/10 | +X |
| ... | ... | ... | ... |
| No AI-Writing Tells | X/10 | X/10 | +X |

Overall: [before]/90 to [after]/90

Still below 8/10: [list any]
Why: [root cause, usually "requires author input" or "structural problem beyond prose"]
```

---

## Pinker's Bogus-Rules Ignore List

Do NOT flag these as problems. They are folklore, not grammar:

- Split infinitives ("to boldly go")
- Ending sentences with prepositions
- Starting sentences with "and", "but", or "because"
- Singular "they"
- Using "which" restrictively
- Contractions in formal writing
- First-person "I" in any context

If the author uses these, leave them alone. If someone else flagged them, note that the rule is bogus.

---

## File Handling

If the input was a file path:

```yaml
questions:
  - question: "How should I save the rewrite?"
    header: "Save"
    multiSelect: false
    options:
      - label: "Overwrite original"
        description: "Replace the original file with the rewrite"
      - label: "Save as new file"
        description: "Save as [original]-styled.md alongside the original"
      - label: "Output inline only"
        description: "Don't save; just show in the conversation"
```

If inline: output the rewrite in the conversation. Do not create a file unless asked. In a headless run, overwrite the original.

---

## Edge Cases

Document is already tight: if the overall score is 80 of 90 or higher on the initial pass, report "no rewrite needed" with the diagnostic. Do not manufacture changes.

Voice conflicts with Pinker: if a Pinker principle would soften the candidate's stated voice in `config/profile.md`, keep the voice. The principles serve the voice.

Technical document with unavoidable jargon: flag curse-of-knowledge for the intended audience only. A doc for engineers can assume engineering terms. A pitch for executives cannot.

Creative or stylistic breaks: if the author deliberately uses a fragment, a long sentence, or a cliche for effect, leave it. Flag only if the break seems accidental.

---

*Based on Steven Pinker, The Sense of Style (2014). This skill operationalizes Pinker's core principles as a scoring rubric and rewrite engine, plus an AI-writing-tells check. It preserves voice; it kills bloat.*

## Antipatterns

Before shipping, check the output against `examples/bad/sense-of-style-antipatterns.md`. Do not skip.
