"""Seed the template bank with LinkedIn post templates.

Templates are deconstructed from high-performing LinkedIn posts by
Lea Turner, Ryan Musselman, Lara Acosta, and Daniel Bustamante.
"""
import asyncio
import logging
import sys

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SEED_TEMPLATES = [
    {
        "name": "Origin Story",
        "content_type": "linkedin",
        "description": "Personal journey post that builds connection through vulnerability and transformation",
        "body": (
            "[TIME_ANCHOR — specific date or period]\n\n"
            "[SCENE_SETTING — what you were doing, who you were]\n\n"
            "[OBSTACLE_OR_DOUBTER — the challenge or person who said no]\n\n"
            "[PIVOTAL_DECISION — what you chose to do differently]\n\n"
            "[RESULTS_CASCADE — specific metrics, achievements, milestones]\n"
            "- [RESULT_1]\n"
            "- [RESULT_2]\n"
            "- [RESULT_3]\n\n"
            "[MORAL — universal lesson or encouragement]\n\n"
            "[EMPOWERMENT_CTA — inspire the reader to act]"
        ),
        "structure_hint": (
            "**Origin Story Post**\n"
            "{time anchor — specific date that grounds the story}\n\n"
            "{scene setting — vivid context, 1-2 sentences}\n\n"
            "{obstacle or doubter — creates tension}\n\n"
            "{pivotal decision — the turning point}\n\n"
            "{results cascade — 3-5 specific achievements}\n\n"
            "{moral — universal takeaway}\n\n"
            "{empowerment CTA — inspire action}"
        ),
        "writeprint": (
            "Conversational and raw. Uses short sentences for punch. "
            "Shifts between past and present tense for immediacy. "
            "Specific numbers and dates for credibility. "
            "Ends with direct address to reader ('So, if there's someone...')."
        ),
        "when_to_use": "When sharing a personal turning point, career pivot, or journey that others can relate to. Best for building trust and connection.",
        "when_not_to_use": "When you need to deliver tactical/how-to content or make a quick point. Origin stories need space to breathe.",
        "customization_guide": "Replace time anchor with your specific date. The obstacle should be concrete (a specific person, event, or moment). Results must include real numbers. The moral should connect your story to the reader's situation.",
        "tags": ["storytelling", "personal-brand", "vulnerability", "career"],
        "ai_generated": False,
    },
    {
        "name": "Blunders & Lessons",
        "content_type": "linkedin",
        "description": "Self-deprecating story about a mistake that teaches a valuable lesson",
        "body": (
            "[SELF_DEPRECATING_HOOK — admit the blunder with humor]\n\n"
            "[SETUP — what you were trying to do]\n\n"
            "[THE_MISTAKE — what went wrong, specific details]\n\n"
            "[CONSEQUENCES — what happened as a result]\n\n"
            "[THE_REALIZATION — the moment you understood what went wrong]\n\n"
            "[LESSON_LEARNED — the universal takeaway]\n"
            "- [LESSON_1]\n"
            "- [LESSON_2]\n"
            "- [LESSON_3]\n\n"
            "[VULNERABILITY_CLOSE — acknowledge growth, invite others to share]"
        ),
        "structure_hint": (
            "**Blunders & Lessons Post**\n"
            "{self-deprecating hook — disarm with humor}\n\n"
            "{setup — brief context, 1-2 sentences}\n\n"
            "{the mistake — vivid, specific details}\n\n"
            "{consequences — real impact}\n\n"
            "{the realization — aha moment}\n\n"
            "{lessons — 2-3 bullet points}\n\n"
            "{vulnerability close — growth acknowledgment}"
        ),
        "writeprint": (
            "British humor and understatement. Uses phrases like 'as blunders go' "
            "and 'fairly substantial.' Builds comedic tension then delivers wisdom. "
            "Casual punctuation — dashes and ellipses for pacing. "
            "Self-aware tone that makes the reader feel safe to fail."
        ),
        "when_to_use": "When you have a genuine mistake to share that others can learn from. Works best when the lesson is universal and the humor is natural.",
        "when_not_to_use": "When the mistake involves others negatively or when the lesson is too niche. Don't force humor if the situation was genuinely traumatic.",
        "customization_guide": "The hook must be genuinely self-deprecating — not humble-bragging. Keep the mistake specific and relatable. Lessons should be actionable, not just 'I learned to be better.'",
        "tags": ["storytelling", "vulnerability", "lessons", "humor"],
        "ai_generated": False,
    },
    {
        "name": "Results Breakdown",
        "content_type": "linkedin",
        "description": "Achievement post with specific metrics that breaks down how results were achieved",
        "body": (
            "[BOLD_CLAIM_HOOK — specific achievement with numbers]\n\n"
            "[CONTEXT — where you started, timeframe]\n\n"
            "[THE_APPROACH — what you did differently]\n"
            "- [STRATEGY_1 — with specific metric]\n"
            "- [STRATEGY_2 — with specific metric]\n"
            "- [STRATEGY_3 — with specific metric]\n\n"
            "[KEY_INSIGHT — the non-obvious lesson]\n\n"
            "[WHAT_MOST_PEOPLE_GET_WRONG — contrarian angle]\n\n"
            "[ACTIONABLE_TAKEAWAY — what the reader can do today]\n\n"
            "[CTA — question or invitation to engage]"
        ),
        "structure_hint": (
            "**Results Breakdown Post**\n"
            "{bold claim — specific number or achievement}\n\n"
            "{context — starting point and timeframe}\n\n"
            "{approach — 3-5 strategies with metrics}\n\n"
            "{key insight — non-obvious lesson}\n\n"
            "{common mistake — what others get wrong}\n\n"
            "{actionable takeaway — one thing to try today}\n\n"
            "{CTA — engagement prompt}"
        ),
        "writeprint": (
            "Direct and confident without being arrogant. Leads with proof. "
            "Uses bullet points for scanability. Numbers in every section. "
            "Shifts from 'I' to 'you' in the second half to make it about the reader. "
            "Ends with a question to drive comments."
        ),
        "when_to_use": "When you have genuine, specific results to share and can break down the how. Best when you can challenge conventional approaches.",
        "when_not_to_use": "When results are vague or unverifiable. Don't use if it reads as a humble-brag without teaching value.",
        "customization_guide": "Every number must be real and specific. The 'what most people get wrong' section is where you differentiate — make it genuinely contrarian. The CTA should invite discussion, not just 'thoughts?'.",
        "tags": ["results", "metrics", "how-to", "credibility"],
        "ai_generated": False,
    },
    {
        "name": "Vulnerability Confession",
        "content_type": "linkedin",
        "description": "Deeply personal post about struggle or transformation that builds authentic connection",
        "body": (
            "[STAT_OR_VISUAL_HOOK — specific number or image reference]\n\n"
            "[THE_CONFESSION — what you've been through]\n\n"
            "[THE_STRUGGLE — raw details, no sugarcoating]\n"
            "- [STRUGGLE_DETAIL_1]\n"
            "- [STRUGGLE_DETAIL_2]\n\n"
            "[THE_TURNING_POINT — what changed]\n\n"
            "[WHERE_YOU_ARE_NOW — current state, with perspective]\n\n"
            "[THE_DEEPER_LESSON — what this taught you about life/work]\n\n"
            "[UNIVERSAL_MESSAGE — connect to the reader's experience]\n\n"
            "[SUPPORTIVE_CTA — encourage, don't preach]"
        ),
        "structure_hint": (
            "**Vulnerability Confession Post**\n"
            "{stat or visual hook — concrete anchor}\n\n"
            "{the confession — honest admission}\n\n"
            "{the struggle — raw, specific details}\n\n"
            "{turning point — what shifted}\n\n"
            "{where you are now — progress, not perfection}\n\n"
            "{deeper lesson — life/work insight}\n\n"
            "{universal message — reader connection}\n\n"
            "{supportive CTA — encourage action}"
        ),
        "writeprint": (
            "Raw and unflinching honesty. Short paragraphs for emotional weight. "
            "Present tense for the struggle, past tense for reflection. "
            "No platitudes — earned wisdom only. "
            "Tone shifts from heavy to hopeful by the end."
        ),
        "when_to_use": "When you've genuinely been through something difficult and have come out the other side with perspective. Must be authentic — readers detect fake vulnerability instantly.",
        "when_not_to_use": "When you're still in the middle of the struggle without perspective. Don't use for minor inconveniences dressed up as hardship.",
        "customization_guide": "The hook must be specific (numbers, dates, or visual anchors). The struggle section should make the reader uncomfortable — that's the point. The lesson must be earned, not borrowed. End with hope, not a sales pitch.",
        "tags": ["vulnerability", "personal-brand", "storytelling", "mental-health"],
        "ai_generated": False,
    },
    {
        "name": "Contrarian Advice",
        "content_type": "linkedin",
        "description": "Challenge conventional wisdom with a provocative take backed by experience",
        "body": (
            "[PROVOCATIVE_HOOK — challenge a widely-held belief]\n\n"
            "[CONVENTIONAL_WISDOM — what everyone says]\n\n"
            "[WHY_IT'S_WRONG — your contrarian argument]\n\n"
            "[EVIDENCE — your experience or data]\n"
            "- [PROOF_POINT_1]\n"
            "- [PROOF_POINT_2]\n"
            "- [PROOF_POINT_3]\n\n"
            "[THE_REAL_ANSWER — what actually works]\n\n"
            "[REFRAME — how to think about it differently]\n\n"
            "[POLARIZING_CTA — take a side, invite debate]"
        ),
        "structure_hint": (
            "**Contrarian Advice Post**\n"
            "{provocative hook — bold claim that challenges status quo}\n\n"
            "{conventional wisdom — what 'everyone knows'}\n\n"
            "{why it's wrong — your counterargument}\n\n"
            "{evidence — 3 proof points from experience}\n\n"
            "{the real answer — what actually works}\n\n"
            "{reframe — new mental model}\n\n"
            "{polarizing CTA — spark debate}"
        ),
        "writeprint": (
            "Confident and slightly confrontational. Uses 'Stop doing X' or 'X is a lie' "
            "framing. Short, punchy sentences for impact. "
            "Backs up bold claims with specific evidence. "
            "Ends by taking a clear side — no fence-sitting."
        ),
        "when_to_use": "When you have genuine experience that contradicts popular advice. Works best when you can back up the contrarian view with results.",
        "when_not_to_use": "When your contrarian take is just being different for attention. Don't use without real evidence or experience to back it up.",
        "customization_guide": "The hook must be genuinely provocative — not clickbait. The conventional wisdom must be something your audience actually believes. Your evidence must be specific and verifiable. The CTA should invite disagreement.",
        "tags": ["contrarian", "thought-leadership", "debate", "advice"],
        "ai_generated": False,
    },
    {
        "name": "Dialogue Scene Hook",
        "content_type": "linkedin",
        "description": "Drop the reader into a conversation or scene that reveals a deeper insight",
        "body": (
            "[SCENE_HOOK — set the moment with sensory detail]\n\n"
            "[DIALOGUE — the conversation that happened]\n"
            "\"[CHARACTER_LINE_1]\"\n"
            "\"[YOUR_RESPONSE_1]\"\n"
            "\"[CHARACTER_LINE_2]\"\n\n"
            "[THE_PAUSE — moment of reflection]\n\n"
            "[WHAT_THEY_REALLY_MEANT — deeper interpretation]\n\n"
            "[THE_LESSON — what you took away]\n\n"
            "[UNIVERSAL_TRUTH — how this applies to the reader]\n\n"
            "[REFLECTIVE_CTA — ask the reader about their own experience]"
        ),
        "structure_hint": (
            "**Dialogue/Scene Post**\n"
            "{scene hook — drop into the moment}\n\n"
            "{dialogue — 3-5 lines of conversation}\n\n"
            "{the pause — moment of reflection}\n\n"
            "{what they really meant — deeper layer}\n\n"
            "{the lesson — personal takeaway}\n\n"
            "{universal truth — reader connection}\n\n"
            "{reflective CTA — invite their story}"
        ),
        "writeprint": (
            "Cinematic and immersive. Uses present tense to drop the reader into the moment. "
            "Short dialogue lines — no speech tags needed. "
            "A reflective pause before the insight. "
            "Gentle, philosophical tone in the lesson section."
        ),
        "when_to_use": "When a real conversation or encounter taught you something unexpected. Best for wisdom that can't be distilled into bullet points — it needs to be experienced.",
        "when_not_to_use": "When the conversation was mundane or the insight is obvious. Don't fabricate dialogue — readers can tell.",
        "customization_guide": "The scene must be specific enough to visualize. Keep dialogue to 3-5 lines max — less is more. The pause/reflection is the emotional pivot — don't rush it. The universal truth should feel discovered, not preached.",
        "tags": ["storytelling", "dialogue", "wisdom", "personal-brand"],
        "ai_generated": False,
    },
    {
        "name": "Listicle Framework",
        "content_type": "linkedin",
        "description": "Structured list post with a question hook and actionable numbered points",
        "body": (
            "[QUESTION_HOOK — ask the question your audience is thinking]\n\n"
            "[CONTEXT — brief setup, 1-2 sentences]\n\n"
            "[NUMBERED_LIST]\n"
            "1. [POINT_1_HEADLINE]\n"
            "   [POINT_1_EXPLANATION — 1-2 sentences]\n\n"
            "2. [POINT_2_HEADLINE]\n"
            "   [POINT_2_EXPLANATION — 1-2 sentences]\n\n"
            "3. [POINT_3_HEADLINE]\n"
            "   [POINT_3_EXPLANATION — 1-2 sentences]\n\n"
            "4. [POINT_4_HEADLINE]\n"
            "   [POINT_4_EXPLANATION — 1-2 sentences]\n\n"
            "5. [POINT_5_HEADLINE]\n"
            "   [POINT_5_EXPLANATION — 1-2 sentences]\n\n"
            "[BONUS_TIP — unexpected extra value]\n\n"
            "[CTA — which point resonates most?]"
        ),
        "structure_hint": (
            "**Listicle Post**\n"
            "{question hook — reader's burning question}\n\n"
            "{context — brief setup}\n\n"
            "{5-7 numbered points with headline + 1-2 sentence explanation}\n\n"
            "{bonus tip — unexpected extra}\n\n"
            "{CTA — which point resonates?}"
        ),
        "writeprint": (
            "Clear and scannable. Each point has a bold headline followed by a brief "
            "explanation. Uses 'you' language throughout. "
            "Conversational but authoritative. "
            "Numbers in the headline for specificity."
        ),
        "when_to_use": "When you have 5+ actionable tips on a topic your audience cares about. Great for establishing expertise and driving saves/bookmarks.",
        "when_not_to_use": "When your points are vague or generic. If each point can't stand alone as useful advice, the post won't work.",
        "customization_guide": "The question hook must be something your audience actually asks. Each point needs a concrete headline — not 'Be consistent' but 'Post 3x per week for 90 days.' The bonus tip should be the most unexpected insight.",
        "tags": ["how-to", "listicle", "actionable", "tips"],
        "ai_generated": False,
    },
    {
        "name": "Hot Take",
        "content_type": "linkedin",
        "description": "Short, punchy opinion post that sparks debate and drives engagement",
        "body": (
            "[PROVOCATIVE_OPENING — strong opinion, no hedging]\n\n"
            "[THE_TAKE — expand on your position in 2-3 sentences]\n\n"
            "[WHY_THIS_MATTERS — connect to a bigger issue]\n\n"
            "[EXAMPLE — one specific instance that proves your point]\n\n"
            "[THE_UNCOMFORTABLE_TRUTH — the thing people don't want to hear]\n\n"
            "[SHARP_CLOSE — land the point with conviction]\n\n"
            "[DEBATE_CTA — invite disagreement]"
        ),
        "structure_hint": (
            "**Hot Take Post**\n"
            "{provocative opening — no hedging}\n\n"
            "{the take — 2-3 sentence expansion}\n\n"
            "{why this matters — bigger picture}\n\n"
            "{example — one specific proof}\n\n"
            "{uncomfortable truth — the hard part}\n\n"
            "{sharp close — conviction}\n\n"
            "{debate CTA — invite pushback}"
        ),
        "writeprint": (
            "Unapologetic and direct. No qualifiers or 'in my opinion.' "
            "Short paragraphs — some just one sentence. "
            "Uses humor or exaggeration for emphasis. "
            "Ends with conviction, not compromise."
        ),
        "when_to_use": "When you have a genuine strong opinion about something in your industry. Best when the take is defensible but will make some people disagree.",
        "when_not_to_use": "When you don't actually believe the take or can't defend it. Don't be controversial for clicks — be controversial because you care.",
        "customization_guide": "The opening must be strong enough to stop scrollers. Keep it under 200 words — hot takes lose power when they're long. The example must be real and specific. Your CTA should genuinely invite opposing views.",
        "tags": ["opinion", "debate", "engagement", "thought-leadership"],
        "ai_generated": False,
    },
    {
        "name": "Community Social Proof",
        "content_type": "linkedin",
        "description": "Celebrate a community milestone or achievement to build social proof and gratitude",
        "body": (
            "[EXCITEMENT_HOOK — milestone number with genuine emotion]\n\n"
            "[CONTEXT — what this milestone means]\n\n"
            "[THE_JOURNEY — how you got here, briefly]\n\n"
            "[GRATITUDE — specific thanks to the community]\n"
            "- [THANK_GROUP_1]\n"
            "- [THANK_GROUP_2]\n"
            "- [THANK_GROUP_3]\n\n"
            "[BEHIND_THE_SCENES — what people don't see]\n\n"
            "[WHAT'S_NEXT — future plans or goals]\n\n"
            "[COMMUNITY_CTA — invite participation or celebration]"
        ),
        "structure_hint": (
            "**Community/Social Proof Post**\n"
            "{excitement hook — milestone with emotion}\n\n"
            "{context — what this means}\n\n"
            "{the journey — brief recap}\n\n"
            "{gratitude — specific thank-yous}\n\n"
            "{behind the scenes — reality check}\n\n"
            "{what's next — forward-looking}\n\n"
            "{community CTA — celebrate together}"
        ),
        "writeprint": (
            "Genuine excitement without being over the top. "
            "ALL CAPS for the milestone number (e.g., 'SEVENTY-TWO!'). "
            "Shifts from celebration to gratitude to vulnerability. "
            "Ends by making it about the community, not you."
        ),
        "when_to_use": "When you hit a genuine milestone (member count, revenue, anniversary). Must be a real celebration with real gratitude.",
        "when_not_to_use": "When the milestone is manufactured or insignificant. Don't celebrate vanity metrics without substance behind them.",
        "customization_guide": "The milestone number is the anchor — make it prominent. Gratitude must be specific (name groups or types of people). The behind-the-scenes section humanizes the achievement. End with what's next to maintain momentum.",
        "tags": ["community", "social-proof", "milestone", "gratitude"],
        "ai_generated": False,
    },
    {
        "name": "Step-by-Step Breakdown",
        "content_type": "linkedin",
        "description": "Tactical breakdown of a process or system with clear numbered steps",
        "body": (
            "[RESULT_HOOK — specific outcome you achieved]\n\n"
            "[CONTEXT — why this matters, who it's for]\n\n"
            "[STEP_BY_STEP_PROCESS]\n"
            "Step 1: [STEP_1_TITLE]\n"
            "[STEP_1_DETAIL — exactly what to do]\n\n"
            "Step 2: [STEP_2_TITLE]\n"
            "[STEP_2_DETAIL — exactly what to do]\n\n"
            "Step 3: [STEP_3_TITLE]\n"
            "[STEP_3_DETAIL — exactly what to do]\n\n"
            "Step 4: [STEP_4_TITLE]\n"
            "[STEP_4_DETAIL — exactly what to do]\n\n"
            "[COMMON_PITFALL — what most people get wrong]\n\n"
            "[RESULTS_PROOF — what happened when you followed this]\n\n"
            "[SAVE_CTA — encourage bookmark/save for later]"
        ),
        "structure_hint": (
            "**Step-by-Step Breakdown Post**\n"
            "{result hook — specific outcome}\n\n"
            "{context — who this is for}\n\n"
            "{4-6 numbered steps with title + detail}\n\n"
            "{common pitfall — what to avoid}\n\n"
            "{results proof — your evidence}\n\n"
            "{save CTA — bookmark prompt}"
        ),
        "writeprint": (
            "Tactical and precise. Each step is concrete and actionable. "
            "Uses 'you' and 'your' to make it feel personalized. "
            "Numbers and specifics throughout. "
            "No fluff — every sentence earns its place."
        ),
        "when_to_use": "When you have a proven process that gets specific results. Best when each step is actionable and the reader can implement immediately.",
        "when_not_to_use": "When your process is too complex for a LinkedIn post or when steps are vague. If a step is 'do research,' it's not specific enough.",
        "customization_guide": "The result hook must be specific and achievable. Each step should pass the 'could I do this today?' test. The common pitfall section is where you add your expert insight. Include your own results as proof.",
        "tags": ["how-to", "tactical", "process", "actionable"],
        "ai_generated": False,
    },
]


async def seed_templates(user_id: str = "uttam"):
    """Seed the template bank with LinkedIn templates."""
    from second_brain.deps import create_deps

    deps = create_deps()

    count = 0
    for tmpl in SEED_TEMPLATES:
        tmpl["user_id"] = user_id
        result = await deps.storage_service.upsert_template(tmpl)
        if result:
            count += 1
            print(f"  Seeded: {tmpl['name']}")
        else:
            print(f"  FAILED: {tmpl['name']}")
    print(f"\nDone -- {count}/{len(SEED_TEMPLATES)} templates seeded.")


if __name__ == "__main__":
    import sys as _sys

    uid = _sys.argv[1] if len(_sys.argv) > 1 else "uttam"
    asyncio.run(seed_templates(uid))
