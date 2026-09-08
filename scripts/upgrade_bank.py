"""One-time, idempotent editorial migration of the original 42-card bank."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Title | display brief | compact brief | illustration
COPY = '''
Reorder with care.|Design a grocery reorder flow that saves time without buying unwanted items again.|Redesign grocery reordering to prevent unwanted repeat purchases.|choice
Compare without tabs.|Help a traveler compare hotels by price, commute, cancellation, and perks in one place.|Help a traveler compare hotels without opening several tabs.|comparison
Make the first sale.|Help a first-time seller turn photos into a clear, fairly priced listing.|Help a first-time seller publish a clear, fairly priced listing.|progress
Help, then verify.|Design an AI intake review that flags missing patient details before staff schedule a visit.|Help clinic staff verify AI flags before scheduling a patient.|trust
Review with evidence.|Help a paralegal check AI-flagged clauses and prepare evidence for an attorney.|Help a paralegal verify AI-flagged contract clauses with evidence.|trust
Explain the flag.|Help a fraud analyst see why a transaction was flagged and choose the right action.|Help an analyst understand and act on a flagged transaction.|trust
What needs action?|Help a shipping manager separate delays that need action now from those that can wait.|Help a manager decide which delayed shipments need action now.|overload
Find the real signal.|Design a product dashboard that turns this week's metrics into a clear decision.|Turn a noisy weekly product dashboard into one clear decision.|overload
Make energy useful.|Turn home energy usage into one or two practical changes a household can make.|Turn home energy data into one practical behavior change.|progress
Pay with confidence.|Make the amount, due date, account, and way to fix a payment mistake unmistakable.|Make a bill payment easy to verify and a mistake easy to fix.|trust
Reroute with confidence.|Help a screen reader user follow a trip and recover when a delay changes the route.|Help a screen reader user replan a trip after a delay.|recovery
Keep the path open.|A document is missing. Design a benefits form that helps people recover without losing progress.|Help a benefits applicant recover from a missing document.|recovery
Who can do what?|Help an admin understand who has access, what they can do, and why.|Help an admin understand and change a person's permissions.|access
Give risks attention.|Design approvals so routine requests move quickly and unusual ones get real scrutiny.|Speed up routine approvals while keeping unusual requests visible.|choice
800 errors. One plan.|Turn a failed data import into a manageable sequence of fixes.|Turn hundreds of data-import errors into manageable fixes.|recovery
Make status useful.|Build a reusable composer for progress, blockers, decisions, and next steps.|Design a reusable status composer for progress and blockers.|progress
A theme that works.|Help a non-designer choose colors and type while keeping the result accessible.|Help a non-designer build an accessible visual theme.|choice
Quiet the noise.|Help people choose useful notifications without deciphering a settings matrix.|Make notification preferences understandable and easy to change.|overload
Find your next lesson.|Organize a learning library around goals and the words learners actually use.|Help learners find their next lesson using their own words.|comparison
Read it. Or act on it.|Organize a patient portal so information and required actions are easy to tell apart.|Separate things to read from actions to take in a patient portal.|choice
Which answer is right?|Help employees find the authoritative answer and understand why it applies to them.|Help an employee find a trustworthy answer in a knowledge hub.|trust
Change one meal.|Help a caregiver adjust recurring meal deliveries without rebuilding every order.|Help a caregiver change a recurring meal order without starting over.|recovery
Get everyone seated.|Help a group choose seats and finish buying tickets before availability changes.|Help a group agree on seats before tickets sell out.|comparison
Let the right person in.|Make temporary home access easy to create, understand, and revoke.|Make temporary home access easy to grant and revoke.|access
Keep the agent in charge.|Help a support agent verify an AI summary, check policy, and edit a draft reply.|Help support agents verify and edit an AI-drafted reply.|trust
Adapt without distortion.|Help a teacher verify facts and learning goals in an AI-adapted lesson.|Help a teacher verify an AI-adapted lesson before sharing it.|trust
Challenge the ranking.|Help hiring staff inspect job evidence and challenge AI ranking assumptions.|Help hiring staff question AI rankings using job evidence.|trust
Who needs a call?|Help a fundraiser spot donors who need attention and choose a useful next action.|Help a fundraiser see which donors need attention next.|overload
Learn from the launch.|Show a creator what worked, what did not, and what to try in the next release.|Turn launch results into a useful decision for the next release.|progress
A leak or a bad sensor?|Help an operator distinguish likely leaks from faulty readings and assign a response.|Help an operator distinguish leaks from faulty sensor readings.|comparison
Keep the conversation clear.|Combine captions, speakers, and slides so people can recover when transcription falters.|Help people follow a live session when captions become unreliable.|recovery
Join without precision.|Make telehealth easy to join with limited dexterity, including camera and audio recovery.|Make a telehealth call easy to join with limited dexterity.|access
Come back with confidence.|Help someone pause an insurance claim and return without remembering every detail.|Help someone resume an insurance claim after a break.|recovery
Keep the team aligned.|Bring incident ownership, decisions, status, and stakeholder updates into one clear workspace.|Keep incident ownership and decisions clear during an outage.|overload
Unblock the next step.|Show what blocks vendor onboarding, who owns it, and which evidence can be reused.|Help a team identify and unblock the next vendor-onboarding step.|progress
Cover the shift fairly.|Help a planner fill staffing gaps without hiding fairness or compliance problems.|Help a planner fill a shift gap while making fairness visible.|comparison
Change many. Safely.|Design a reusable table for filtering, selecting, editing, and safely changing many records.|Design safe bulk editing for a reusable data table.|choice
Make the upgrade clear.|Help teams find old components, understand replacements, and track a safe migration.|Help teams replace deprecated components without losing track.|progress
Save before you sync.|Design an inspection form that saves offline, shows sync state, and resolves conflicts.|Help inspectors save offline and resolve conflicting edits.|recovery
Start with a resident.|Organize city services around what residents need, rather than department names.|Organize a city services site around residents' needs.|access
Choose together.|Organize a streaming home for personal taste, shared viewing, ages, and unfinished shows.|Help a household find something suitable to watch together.|choice
Find the way forward.|Connect concepts, instructions, and troubleshooting so developers can recover without losing context.|Connect developer guides and troubleshooting without dead ends.|recovery
Fix one frustrating step.|Think of an app you used today. Identify one confusing step and sketch a clearer alternative.|Find one confusing step in an app. Sketch a clearer alternative.|friction
Why enter it twice?|Notice a form that asks for the same information twice. Redesign it to remove that extra work.|Find repeated data entry. Redesign the flow to remove it.|friction
Make the label make sense.|Find a label you had to interpret. Rewrite it and show how you would check understanding.|Find a confusing label. Rewrite it in words users understand.|trust
Show what just happened.|Recall an action with unclear feedback. Design a state that confirms what happened and what comes next.|Find unclear feedback. Show what happened and what comes next.|progress
Remove a dead end.|Find a search with no useful results. Help the person recover without starting over.|Find an unhelpful empty search. Design a useful next step.|recovery
Make a mistake fixable.|Recall an everyday mistake in an interface. Design a clear, low-effort way to undo it.|Find an interface mistake that is hard to undo. Make recovery easy.|recovery
Make saying no easy.|Find a screen that pressures people to accept. Make accepting and declining equally clear.|Find a pressured choice. Make accepting and declining equally clear.|choice
Show the full price.|Notice a checkout that reveals fees late. Redesign it so the total is clear before commitment.|Find late checkout fees. Show the full price before commitment.|trust
Let people leave.|Find a difficult cancellation flow. Redesign it so people can leave without unnecessary obstacles.|Find a difficult cancellation flow. Remove unnecessary obstacles.|access
Make consent a choice.|Find preselected or bundled consent. Design separate, understandable choices people control.|Find bundled consent. Give people separate, understandable choices.|choice
Remove the false urgency.|Find a countdown or scarcity claim that pressures a decision. Offer truthful, useful context instead.|Find pressure from urgency cues. Replace it with truthful context.|trust
Explain what is shared.|Find a request for more personal data than a task needs. Explain the purpose and make extras optional.|Find excessive data collection. Explain it and make extras optional.|access
'''.strip().splitlines()


def main():
    path = ROOT / 'data/prompts.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    prompts = payload['prompts']
    for index, line in enumerate(COPY):
        title, brief, compact, visual = line.split('|')
        if index >= len(prompts):
            category = 'Everyday UX' if index < 48 else 'Dark Patterns'
            prompts.append({
                'id': f'ddd-{index + 1:03}', 'mode': category,
                'industry': 'Everyday digital products',
                'primary_user': 'A person using an everyday app or website',
                'business_goal': 'Help people complete their task with confidence',
                'constraint': 'Use an example you observed; explain assumptions without inventing evidence.',
                'problem': brief, 'ai_capability': '',
                'watch_for': ('Personal taste mistaken for a usability problem' if index < 48 else
                              'Replacing one pressured choice with another'),
                'required_patterns': ['Observed example', 'User impact', 'Alternative design', 'Validation approach', 'Recovery state', 'Tradeoff'],
                'deliverables': ['Describe the observation', 'Sketch the alternative', 'Explain how to evaluate it'],
                'interview_focus': 'Explain who benefits, what improves, and how you would know.'
            })
        prompts[index].update(display_title=title, display_brief=brief,
                              compact_brief=compact, visual_key=visual,
                              provenance={'source': 'curated', 'version': '2'})
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
