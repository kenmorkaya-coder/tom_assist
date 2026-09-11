"""Post-selection authored surfaces for a single new held-out pass."""
def render(f,v):
    a,b,c,d=[v[k] for k in ('a','b','c','d')];para=v['para'];n=v['value']
    if f in ('quantity','comparator','polarity'):
        bound=v['condition'];modal='must not' if v['neg'] else 'must'
        return (f'The applicable trigger is that {bound}; whenever this happens, {a} {modal} stop.' if para else
                f'{a} {modal} stop upon satisfaction of this trigger: {bound}.')
    if f in ('recipient','authority'):
        who=v['person'];trigger=v['trigger']
        if f=='recipient':
            return (f'If {trigger}, stopping {a} is mandatory, as is a notification addressed to {who}.' if para else
                    f'The condition {trigger} requires a stop to {a} and a notification addressed to {who}.')
        return (f'The stop instruction for {a} was issued by {who}. It requires stopping whenever {trigger}.' if para else
                f'An instruction from {who} requires {a} to stop if {trigger}.')
    if f=='unless':
        trigger=v['trigger']
        return (f'{a} may continue, but that permission has an exception: {trigger}.' if para else
                f'Except when {trigger}, permission is given for {a} to continue.')
    if f in ('nested','nested_boolean','negation_scope'):
        cond=v['condition']
        return (f'Apply this requirement to {a}: it must stop if {cond}.' if para else
                f'The requirement to stop {a} applies in exactly this case: {cond}.')
    if f=='direction':
        source,target=v['source'],v['target']
        return (f'The factor causing {target} is {source}.' if para else
                f'{target} results from {source}.')
    if f=='temporal':
        order=v['order']
        return (f'{a} must perform an inspection of {b}. That inspection is scheduled {order} {c} is allowed to continue.' if para else
                f'An inspection of {b} is required of {a}, {order} the permitted continuation of {c}.')
    if f=='revision':
        old,new=v['old'],v['new']
        return (f'Revision {old} contains the obligation for {a} to stop. It is superseded by {new}, which gives permission for {a} to continue.' if para else
                f'{old} imposes a stop on {a}. {new} allows {a} to continue, replacing the requirement in {old}.')
    if f=='time':
        date=v['date']
        return (f'The required inspection by {a} of {b} is set for {date}.' if para else
                f'On {date}, {a} is under an obligation to inspect {b}.')
    if f=='approval':
        person=v['person']
        return (f'{a} is permitted to continue unless approval to stop it is given by {person}.' if para else
                f'There is permission for {a} to continue, with the exception of {person} approving a stop for those works.')
    if f=='conflict':
        other='may continue' if v['changed'] else 'must not stop'
        return (f'One rule states that {a} must stop. The conflicting rule states that {a} {other}.' if para else
                f'For {a}, the first instruction requires stopping, whereas the conflicting second instruction says it {other}.')
    if f=='multi_quantity':
        x,y=v['v1'],v['v2']
        return (f'{a} is required to stop when {b} registers over {x} mm/s. If that same monitor registers over {y} mm/s, {c} must receive notification.' if para else
                f'The stop requirement for {a} is triggered by {b} exceeding {x} mm/s; the notification requirement for {c} is triggered by that monitor exceeding {y} mm/s.')
    if f=='unit_equivalence':
        amount,unit=v['amount'],v['unit']
        return (f'{a} has an obligation to stop on a reading of {b} exceeding {amount} {unit}.' if para else
                f'If {b} measures over {amount} {unit}, stopping {a} is required.')
    if f=='paragraph':
        cap=v['cap']
        return (f'{a} is allowed to continue with {b} measuring under {n} mm/s. If the same measurement exceeds {n} mm/s, a stop to those works is required, together with a notification to {c}. The separate permission for {d} limits its rate to {cap} L/min.' if para else
                f'Continuation is permitted for {a} as long as {b} remains below {n} mm/s. Readings above {n} mm/s at that monitor require both stopping {a} and notifying {c}. {d} is allowed with its rate capped at {cap} L/min.')
    if f=='comparison_bounds':
        phrase=v['phrase']
        return (f'Whenever a measurement of {b} is {phrase} {n} mm/s, the stop requirement applies to {a}.' if para else
                f'The rule requires {a} to stop when {b} measures {phrase} {n} mm/s.')
    if f=='notification_roles':
        actor,issuer,recipient=[v[k] for k in ('actor','issuer','recipient')]
        return (f'A directive from {issuer} requires {actor} to stop {a} and deliver a notification to {recipient} when {b} exceeds {n} mm/s.' if para else
                f'{actor} must, under a directive issued by {issuer}, stop {a} and inform {recipient} if {b} rises above {n} mm/s.')
    raise ValueError(f)
