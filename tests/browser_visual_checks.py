"""Shared Chromium checks for rendered text contrast and reduced motion."""
from pathlib import Path


AUDIT = Path(__file__).with_name("premium_accessibility.js").read_text("utf8")


def contrast(page, selector, view):
    result = page.locator(selector).evaluate(AUDIT)
    assert result["checked"], (view, selector)
    rows = result["checked"]
    return {
        "surface": selector,
        "view": view,
        "checked": len(rows),
        "minimum_ratio": round(min(r["ratio"] for r in rows), 3),
        "failed": [r for r in rows if not r["pass"]],
        "unresolved": result["unresolved"],
    }


def no_motion(page):
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    # Steady layout and actively loading UI are both sampled by the caller.
    return page.evaluate("""()=>document.getAnimations().filter(a=>a.playState==='running' && (
      Number(a.effect?.getComputedTiming().activeDuration)>20 || a.effect?.getComputedTiming().iterations===Infinity)).
      map(a=>({name:a.animationName||a.transitionProperty||'animation',target:a.effect?.target?.id||a.effect?.target?.tagName}))""")
