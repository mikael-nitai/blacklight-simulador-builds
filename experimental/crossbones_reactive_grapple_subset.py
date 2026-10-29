"""Partial Crossbones adapter with limits of the newer reactive grapple host."""

from dataclasses import replace

from .crossbones_grapple_subset import build_crossbones_grapple_subset


def build_crossbones_reactive_grapple_subset(evidence, *, accept_incomplete):
    subset = build_crossbones_grapple_subset(evidence, accept_incomplete=accept_incomplete)
    obsolete = {'The grapple host restricts actors in a hold to escape, release or wait.',
                'Carrying, attacking while holding and multiple simultaneous holds are not implemented.'}
    if not obsolete.issubset(subset.assumptions):
        raise ValueError('Expected earlier host limitations are missing')
    assumptions = tuple(item for item in subset.assumptions if item not in obsolete) + (
        'Close attacks and miss reactions between the two held actors are modeled.',
        'Carrying, knockback, self-hit on a miss, third parties and multiple holds are not modeled.',
        'A hold persists when the holder is Stunned in this experimental host.')
    return replace(subset, assumptions=assumptions)
