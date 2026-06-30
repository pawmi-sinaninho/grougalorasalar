# REMAINING UNKNOWN RULES AND SAFE DEFAULTS

The AP, charge, spell-name, movement, projection, collision-priority, solo-scope and Crocoburio-track rules are no longer unknown. They are fixed by `dofuspourlesnoobs-observed-v1.0.0`.

Only visual values not supported by a calibrated cue may remain unknown. In particular, the spell bar may report an available spell without inventing an exact positive charge count. This does not permit manual AP, spell-state, pillar or pattern confirmation in the normal UI; unresolved recognition must fail safely or use the hidden debug mode.
