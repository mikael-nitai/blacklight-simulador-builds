"""Larger explicitly incomplete Crossbones subset for the experimental grapple host."""

from dataclasses import replace

from .crossbones_subset import build_crossbones_stopping_subset


def build_crossbones_grapple_subset(evidence, *, accept_incomplete):
    base = build_crossbones_stopping_subset(evidence, accept_incomplete=accept_incomplete)
    if 'Grappling Technique' not in base.omitted_powers:
        raise ValueError('Verified Grappling Technique is missing')
    return replace(base,
        profile=replace(base.profile, powers=base.profile.powers | {'grappling_technique'}),
        included_powers=tuple(sorted(set(base.included_powers) | {'Grappling Technique'})),
        omitted_powers=tuple(power for power in base.omitted_powers if power != 'Grappling Technique'),
        assumptions=base.assumptions + (
            'The grapple host restricts actors in a hold to escape, release or wait.',
            'Carrying, attacking while holding and multiple simultaneous holds are not implemented.',
            'Shield and escape trigger identity is an explicitly selected hypothesis.',))
