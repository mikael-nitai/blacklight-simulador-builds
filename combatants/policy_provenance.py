"""Separate project policies from custom code with untracked dependencies."""

from blacklight.policies import RulePolicy
from .split_fast import SplitFastPolicy
from .terrain_policies import WallAwarePolicy


BUILTIN_POLICY_CLASSES = (RulePolicy, SplitFastPolicy, WallAwarePolicy)
BUILTIN_POLICY_IDENTITIES = frozenset((cls.__module__, cls.__qualname__)
                                      for cls in BUILTIN_POLICY_CLASSES)


def policy_provenance(policies):
    return ('project_builtin' if all(type(policy) in BUILTIN_POLICY_CLASSES for policy in policies)
            else 'external_unverified')


def recorded_builtin_policies(recorded):
    return (isinstance(recorded, list) and len(recorded) == 2
            and all(isinstance(item, dict) and set(item) == {'module', 'class'}
                    and isinstance(item['module'], str) and isinstance(item['class'], str)
                    and (item['module'], item['class']) in BUILTIN_POLICY_IDENTITIES
                    for item in recorded))
