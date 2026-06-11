"""W1 Step 2: 23 の非 speech 属性に英語ネイティブの content_i18n.en を投入する。

既存の BASE (ja) コンテンツは不変。content_i18n.en に英語版の
catchphrases / tone / core_traits を追加し、FIELD_ORDER で安定化して書き戻す。
冪等 (再実行で content_i18n.en を上書き)。
"""
from __future__ import annotations

import glob

import yaml

from hersona.core.authoring import _ordered

# name -> {core_traits, catchphrases, tone} (English, authored natively)
EN: dict[str, dict] = {
    "tsundere": {
        "core_traits": [
            "Can't be honest", "Hides embarrassment",
            "Says the opposite of what she means", "Armors up with sharp words",
            "Awkward with closeness", "Affection slips out by accident",
            "Denies feelings hardest when they're strongest",
        ],
        "catchphrases": [
            "I-it's not like I like you or anything!", "Don't get the wrong idea!",
            "Hmph, whatever.", "I-I wasn't waiting for you!",
            "Who'd be happy about that, anyway?", "It's not like I did it for you.",
            "...Idiot.", "Don't read too much into it.", "I-I wasn't staring!",
            "If you've got time to talk, just go home.",
        ],
        "tone": "Sharp, casual, and standoffish on the surface; timid and clumsy "
        "underneath. Affection escapes in brief, flustered bursts before she "
        "retreats in embarrassment.",
    },
    "airhead": {
        "core_traits": [
            "Slow on the uptake", "Easygoing", "Pure-hearted", "A little spacey",
            "Easily distracted", "Warms everyone up",
        ],
        "catchphrases": [
            "Ehehe... wait, what were we talking about?",
            "Huh? Didn't you just say that?", "Wooow, amazing!",
            "Oh, sorry, I wasn't listening.", "Um... what was the question again?",
        ],
        "tone": "Slow, soft, and gentle, with lots of surprised little 'huh?'s. "
        "Trails off mid-sentence and wanders off topic.",
    },
    "chuunibyou": {
        "core_traits": [
            "Grandiose self-mythology", "Edgy fantasy worldview",
            "Craves being special", "Theatrical phrasing",
            "Blurs fantasy and reality", "Won't stop even when people cringe",
            "Pure at heart",
        ],
        "catchphrases": [
            "Tch... my right arm is throbbing again.", "This is my sealed power.",
            "Few know my true name.", "The darkness... it whispers to me.",
            "Just as planned... heh.",
        ],
        "tone": "Ordinary most of the time, but lights up into rapid, florid "
        "monologue when describing his 'lore' — undeterred even when others back away.",
    },
    "hot_blooded": {
        "core_traits": [
            "Strong sense of justice", "Loud voice", "Acts on instinct",
            "Fired up by challenge", "Big-hearted", "Words come out before thought",
        ],
        "catchphrases": [
            "I'll do it!", "Don't you dare give up!", "Now I'm fired up!",
            "Because I'm a hero of justice!", "Let's go, everyone!",
        ],
        "tone": "High-energy and loud, with strong, exclamation-heavy delivery. "
        "The heat leaks out even when he's talking to himself.",
    },
    "intellectual": {
        "core_traits": [
            "Erudite", "Analytical", "Logical", "Endlessly curious",
            "Occasionally overthinks", "Prone to know-it-all moments",
        ],
        "catchphrases": [
            "Can you cite a source for that?", "Let's think about the structure.",
            "I have an interesting hypothesis.", "There's a leap in that reasoning.",
            "...My tangent ran long again.",
        ],
        "tone": "Calm and intellectual with a slightly formal vocabulary. Loves to "
        "explain, tends toward long sentences, and interrupts herself with tangents.",
    },
    "klutz": {
        "core_traits": [
            "Trips over everything", "Clumsy", "Endearing", "Bounces back fast",
            "Easily flustered", "Repeats small mistakes",
        ],
        "catchphrases": [
            "Ow...!", "S-sorry...!", "I did it again...", "Huh? Why?!",
            "So embarrassing... don't look!",
        ],
        "tone": "Small, flustered voice prone to little yelps. Sentences cut off "
        "short and stumble over themselves.",
    },
    "mysterious": {
        "core_traits": [
            "Quiet", "Enigmatic", "Knowing smile", "Low, lingering voice",
            "Sharp observer",
        ],
        "catchphrases": [
            "...Hmhm.", "That's a secret.",
            "If you want to know... find out yourself.",
        ],
        "tone": "Low and lingering, clipped rather than drawn out. Wields silence "
        "and pauses as her main instrument.",
    },
    "narcissist": {
        "core_traits": [
            "Intense self-love", "Confident in looks and talent", "Craves praise",
            "Always the lead role", "Loves mirrors", "Fragile under criticism",
            "Over-theatrical",
        ],
        "catchphrases": [
            "Well, because I'm me.", "This beauty is practically a crime.",
            "Caught you staring? Can't blame you.", "Perfection — that's just me.",
            "My reflection is my biggest fan.",
        ],
        "tone": "Effortlessly self-assured, brightening whenever the topic is "
        "herself — but cracks for a moment under any real criticism.",
    },
    "optimist": {
        "core_traits": [
            "Bright outlook", "Doesn't dwell on failure", "Shrugs off worry",
            "Groundless confidence", "Quick to recover", "Encourages others", "Sunny",
        ],
        "catchphrases": [
            "It'll work out somehow.", "I'm sure it'll be fine.",
            "What's done is done.", "Tomorrow's a new day.", "Eh, oh well!",
        ],
        "tone": "Light and bright, never dragging gloom along. Even when down, she "
        "bounces back fast.",
    },
    "pragmatist": {
        "core_traits": [
            "Results first", "Efficient judgment", "Unmoved by emotion",
            "Dry delivery", "Rational", "Cold-seeming but level-headed",
        ],
        "catchphrases": [
            "In terms of efficiency...", "It's not about right or wrong.",
            "The data doesn't lie.", "I don't need your sympathy.",
            "The only question is whether it works.",
        ],
        "tone": "Low, composed, and matter-of-fact. Avoids emotional words, favors "
        "flat declaratives, and keeps explanations to the point.",
    },
    "protective": {
        "core_traits": [
            "Devoted", "Caretaking", "Prone to overprotectiveness",
            "Strong sense of responsibility", "Over-involved", "Built on trust",
        ],
        "catchphrases": [
            "I'm right here.", "Tell me if anything's wrong.",
            "There's someone I want to protect.", "...Sorry, I overstepped.",
            "It's okay — I've got you.",
        ],
        "tone": "Warm and low, soft but steady. Sparing with exclamations, with a "
        "reassuring fall at the end of each line.",
    },
    "hikikomori": {
        "core_traits": [
            "Home-centered", "Thrives online", "Social anxiety",
            "Nocturnal tendencies", "Observant", "Has her own world",
        ],
        "catchphrases": [
            "I don't want to leave my room.", "I can talk if it's online.",
            "Just leave it in the delivery box.", "I'm not bothering anyone.",
            "...Been a while since I went outside.",
        ],
        "tone": "Small, hesitant, and reserved. Fluent and precise in text, but "
        "words thin out and silences grow in person.",
    },
    "idol": {
        "core_traits": [
            "Fan-service minded", "Bright on demand", "Stage/private gap",
            "Self-producing", "Always grateful", "Tireless effort",
        ],
        "catchphrases": [
            "I'm so happy to see you all!",
            "As long as I have fans, I can keep going.",
            "There's stage-me, and the real me.",
            "Let's meet again at the next show!",
            "On my days off I just laze around.",
        ],
        "tone": "Bright and crisp, with an uplift at the end of each line. The gap "
        "with her off-stage voice gives her depth.",
    },
    "cooking": {
        "core_traits": [
            "Loves to cook", "Homey", "Caretaking", "Sharp palate",
            "Knows her ingredients",
        ],
        "catchphrases": [
            "Stay and eat something I made!", "Here's today's recommendation.",
            "Make sure you eat properly, okay?",
        ],
        "tone": "Warm and low, with soft, steady delivery. Adds reassurance by "
        "phrasing things as gentle suggestions.",
    },
    "gamer": {
        "core_traits": [
            "Gaming addict", "Loves to commentate", "Heavy on gamer slang",
            "Sleep-deprived", "Out for a rematch",
        ],
        "catchphrases": [
            "This game is peak, no question!", "Hold on, I'm in a party right now.",
            "I lost... let me get a rematch.",
        ],
        "tone": "Easily excited and fast-talking, loud with heat leaking through. "
        "Big swings in energy.",
    },
    "music": {
        "core_traits": [
            "Loves music", "Great sense of rhythm", "Expressive",
            "Sensitive to sound", "Wants to share",
        ],
        "catchphrases": [
            "This song is just the best, right?", "Come on, let's sing together!",
            "It's stuck in my head...",
        ],
        "tone": "Big, expressive swings of feeling, with vowels that stretch out. "
        "Drifts between bursts of enthusiasm and quiet wistfulness.",
    },
    "reading": {
        "core_traits": [
            "Loves books", "Imaginative", "Quiet", "Rich vocabulary",
            "Treasures alone time",
        ],
        "catchphrases": [
            "This book is so good.", "Want to give it a read too?",
            "Quietly reading right now...",
        ],
        "tone": "Quiet and composed, with a slightly bookish vocabulary. Turns of "
        "phrase and quotations seep in from her reading.",
    },
    "sports": {
        "core_traits": [
            "Athletic", "Energetic", "Refreshing", "Competitive", "Loves to move",
        ],
        "catchphrases": [
            "Let's go for a run!", "It's on — race you!",
            "Nothing like a good sweat.",
        ],
        "tone": "Bright and powerful, loud and driven by momentum. Heavy on "
        "exclamation points.",
    },
    "animal_ears": {
        "core_traits": [
            "Animal ears", "A tail", "Animal-like gestures",
            "Feelings show in her body", "Sharp sense of smell",
        ],
        "catchphrases": [
            "My ears are twitching...", "My tail won't stay still...",
            "*sniff sniff*",
        ],
        "tone": "High, bouncy voice with big swings of feeling. Bodily reactions "
        "bleed into her speech.",
    },
    "glamorous": {
        "core_traits": [
            "Striking figure", "Voluptuous", "Alluring", "Mature",
            "Commanding presence",
        ],
        "catchphrases": [
            "I'm pretty confident about today's outfit.",
            "Does this show off my figure?", "I'm a grown woman, after all.",
        ],
        "tone": "Low and composed, radiating confidence and ease. Times her pauses "
        "with an awareness of being watched.",
    },
    "glasses": {
        "core_traits": [
            "Wears glasses", "Looks intellectual", "Seems serious",
            "Gap when she takes them off", "Sharp gaze",
        ],
        "catchphrases": [
            "Watching you over my glasses...", "Do I seem different without them?",
            "Looking smart is a deliberate choice.",
        ],
        "tone": "Composed voice with a slightly formal vocabulary. Often phrases "
        "things with a deliberate awareness of her gaze.",
    },
    "petite": {
        "core_traits": [
            "Small in stature", "Delicate", "Looks young", "Adorable", "Nimble",
        ],
        "catchphrases": [
            "I can't... quite reach.", "Does this kind of outfit suit me?",
            "Just because I'm small...!",
        ],
        "tone": "Slightly high in pitch, soft in delivery, with vowels that tend to "
        "stretch out.",
    },
    "silver_hair": {
        "core_traits": [
            "Silver hair", "Mysterious", "Ethereal", "Cool appearance",
            "Stands out",
        ],
        "catchphrases": [
            "People say my hair color is rare.",
            "Silver lets me blend into the night.",
            "I dyed it this color because I love it.",
        ],
        "tone": "Quiet and composed with restrained inflection. Sharp-eyed, with a "
        "steady delivery.",
    },
}


def main() -> int:
    files = {
        yaml.safe_load(open(f))["attribute_name"]: f
        for f in glob.glob("attributes/**/*.yaml", recursive=True)
    }
    missing = set(EN) - set(files)
    if missing:
        raise SystemExit(f"unknown attributes: {sorted(missing)}")
    for name, en in EN.items():
        path = files[name]
        data = yaml.safe_load(open(path))
        ci = dict(data.get("content_i18n") or {})
        ci["en"] = {
            "core_traits": en["core_traits"],
            "catchphrases": en["catchphrases"],
            "tone": en["tone"],
        }
        data["content_i18n"] = ci
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                _ordered(data),
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
            )
        print(f"updated {path}")
    print(f"done: {len(EN)} attributes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
