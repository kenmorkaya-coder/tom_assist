"""Authored post-selection wording; no model generations or predictions."""
def render(f,v):
    a,b,c,d=[v[x] for x in ('a','b','c','d')];p=v['para'];value=v['value']
    if f in ('quantity','comparator','polarity'):
        cond=v['condition'];modal='prohibited' if v['neg'] else 'required'
        return (f'Operational limit: {cond}. In that event, {a} is {modal} to stop.' if p else
                f'It is {modal} to stop {a} whenever the following applies: {cond}.')
    if f in ('recipient','authority'):
        who=v['person'];trigger=v['trigger']
        if f=='recipient':
            return (f'A reading for which {trigger} imposes two duties: stop {a}, and notify {who}.' if p else
                    f'{a} must stop in the event that {trigger}. This event also makes it mandatory to notify {who}.')
        return (f'{who} is issuing this instruction: stop {a} whenever {trigger}.' if p else
                f'This mandatory rule comes from {who}: {a} must stop in the event that {trigger}.')
    if f=='unless':
        trigger=v['trigger']
        return (f'Permission to continue applies to {a}, with an exception when {trigger}.' if p else
                f'{a} is permitted to continue; however, the exception to that permission is that {trigger}.')
    if f in ('nested','nested_boolean','negation_scope'):
        cond=v['condition']
        return (f'The test is {cond}. If it is satisfied, {a} must stop.' if p else
                f'Stopping {a} is required when this combined test is true: {cond}.')
    if f=='direction':
        src=v['source'];dst=v['target']
        return (f'{dst} has the following cause: {src}.' if p else f'{src} is the causal origin of {dst}.')
    if f=='temporal':
        order=v['order']
        return (f'Inspection of {b} by {a} is mandatory. Place that inspection {order} the allowed continuation of {c}.' if p else
                f'{a} must inspect {b}. Continued operation of {c} is permitted; the inspection takes place {order} it.')
    if f=='revision':
        old=v['old'];new=v['new']
        return (f'{old} requires stopping {a}. The superseding version {new} instead permits {a} to continue.' if p else
                f'Under {old}, {a} must stop. Under the replacement revision {new}, {a} may continue; {new} supersedes {old}.')
    if f=='time':
        date=v['date']
        return (f'{date} is the scheduled date on which {a} must inspect {b}.' if p else
                f'An inspection of {b} is required of {a}, scheduled for {date}.')
    if f=='approval':
        who=v['person']
        return (f'{a} has permission to continue. The exception is approval by {who} to stop it.' if p else
                f'For {a}, continuation is permitted except in the case that {who} approves stopping those works.')
    if f=='conflict':
        second='may continue' if v['changed'] else 'must not stop'
        return (f'The first instruction requires {a} to stop. In conflict with it, the other instruction says {a} {second}.' if p else
                f'Two conflicting instructions concern {a}: it must stop under the first, and it {second} under the second.')
    if f=='multi_quantity':
        x,y=v['v1'],v['v2']
        return (f'{a} must stop for a value of {b} above {x} mm/s. For the same sensor, a value above {y} mm/s requires notification to {c}.' if p else
                f'A value above {x} mm/s at {b} requires a stop for {a}; a value above {y} mm/s at that sensor requires a notification to {c}.')
    if f=='unit_equivalence':
        amount,unit=v['amount'],v['unit']
        return (f'The mandatory stop for {a} is triggered by {b} being above {amount} {unit}.' if p else
                f'At values of {b} over {amount} {unit}, {a} is obliged to stop.')
    if f=='paragraph':
        cap=v['cap']
        return (f'{a} can continue with permission while {b} is less than {value} mm/s. A value greater than {value} mm/s on that measurement requires stopping those works and notifying {c}. Separately, {d} may operate subject to an upper limit of {cap} L/min.' if p else
                f'Operating permission for {a} allows continuation while {b} stays under {value} mm/s. If that sensor rises over {value} mm/s, {a} must stop and {c} must be notified. For {d}, operation is permitted with a maximum rate of {cap} L/min.')
    if f=='comparison_bounds':
        phrase=v['phrase']
        return (f'Stop {a} as a requirement whenever {b} is {phrase} {value} mm/s.' if p else
                f'{a} is required to stop upon a reading of {b} that is {phrase} {value} mm/s.')
    if f=='notification_roles':
        actor,issuer,recipient=[v[k] for k in ('actor','issuer','recipient')]
        return (f'{issuer} orders the following response by {actor}: stop {a} and notify {recipient} whenever {b} exceeds {value} mm/s.' if p else
                f'Instruction originator: {issuer}. If {b} exceeds {value} mm/s, {actor} is required by that instruction to stop {a} and notify {recipient}.')
    raise ValueError(f)
