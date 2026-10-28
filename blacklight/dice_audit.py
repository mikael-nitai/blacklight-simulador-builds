"""Independent checks for recorded d616 reroll histories.

Only the final three dice and reroll ledger are needed. This module does not
import the simulator's dice resolver or decide a policy's choice of edge.
"""


def _quality(index, face):
    return (6, 1) if index == 1 and face == 1 else (face, 0)


def audit_rerolls(event, *, edges=None, troubles=None):
    seq = event.get('seq')
    issues = []
    roll, traces = event.get('roll'), event.get('rerolls')
    if (not isinstance(roll, (tuple, list)) or len(roll) != 3
            or any(type(face) is not int or not 1 <= face <= 6 for face in roll)
            or not isinstance(traces, (tuple, list))):
        return [f'event {seq}: invalid dice or reroll ledger']
    if edges is not None and (type(edges) is not int or edges < 0):
        return [f'event {seq}: invalid edge count']
    if troubles is not None and (type(troubles) is not int or troubles < 0):
        return [f'event {seq}: invalid trouble count']
    for trace in traces:
        if (not isinstance(trace, dict) or trace.get('kind') not in ('edge', 'trouble')
                or type(trace.get('index')) is not int or trace['index'] not in (0, 1, 2)
                or any(type(trace.get(key)) is not int or not 1 <= trace[key] <= 6
                       for key in ('original', 'rolled', 'kept'))):
            return [f'event {seq}: invalid reroll record']

    # Reconstruct the unrecorded initial roll from the final roll. This also
    # catches a broken chain when the same die was rerolled more than once.
    current = list(roll)
    for trace in reversed(traces):
        index = trace['index']
        if current[index] != trace['kept']:
            issues.append(f'event {seq}: reroll chain disagrees with final dice')
        current[index] = trace['original']
    initial = tuple(current)
    for trace in traces:
        index = trace['index']
        old, new = trace['original'], trace['rolled']
        if trace['kind'] == 'trouble':
            if tuple(current) == (6, 1, 6):
                issues.append(f'event {seq}: reroll applied to ultimate Fantastic')
            strongest = max(range(3), key=lambda i: (_quality(i, current[i]), -i))
            if index != strongest:
                issues.append(f'event {seq}: trouble did not reroll the strongest die')
            expected = new if _quality(index, new) < _quality(index, old) else old
        else:
            expected = new if _quality(index, new) > _quality(index, old) else old
        if current[index] != old or trace['kept'] != expected:
            issues.append(f'event {seq}: reroll kept an impossible die face')
        current[index] = trace['kept']

    if edges is not None and troubles is not None:
        net = edges - troubles
        if net > 0 and (len(traces) > net or any(t['kind'] != 'edge' for t in traces)):
            issues.append(f'event {seq}: reroll exceeds available edges')
        elif net < 0:
            required = 0 if initial == (6, 1, 6) else -net
            if len(traces) != required or any(t['kind'] != 'trouble' for t in traces):
                issues.append(f'event {seq}: reroll does not account for all troubles')
        elif net == 0 and traces:
            issues.append(f'event {seq}: reroll recorded after edges and troubles cancel')
    return issues
