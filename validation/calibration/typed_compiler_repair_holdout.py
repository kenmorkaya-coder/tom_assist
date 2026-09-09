"""Fresh manually authored compiler controls, fixed before repaired scores.

Uses only fixture-construction helpers from the frozen experiment. These are
teacher-supplied events, not claimed outputs of an English extraction model.
"""


def cases(b):
    return (
        b.obligation_case("fresh_quantity_compound", "quantity_change", "resin preparation", "the storekeeper", (
            "retain at most 250 kilograms of resin", "retain at most 125 kilograms of resin", "retain at most 500 kilograms of resin",
        ), "retain no more than one hundred and twenty-five kilograms of resin", quantity_values=(250, 125, 500)),
        b.obligation_case("fresh_quantity_flow", "quantity_change", "flushing operations", "the drainage technician", (
            "keep flow below 35 litres per second", "keep flow below 70 litres per second", "keep flow below 105 litres per second",
        ), "maintain flow lower than seventy litres per second", quantity_values=(35, 70, 105)),
        b.obligation_case("fresh_quantity_cover", "quantity_change", "reinforcement inspection", "the steel fixer", (
            "provide at least 45 millimetres of cover", "provide at least 30 millimetres of cover", "provide at least 60 millimetres of cover",
        ), "supply a minimum of thirty millimetres of cover", quantity_values=(45, 30, 60)),
        b.obligation_case("fresh_alternative_dock", "named_alternative", "night unloading", "the freight coordinator", (
            "unload at Dock Birch", "unload at Dock Willow", "unload at Dock Aspen",
        ), "deliver the cargo to Dock Willow"),
        b.obligation_case("fresh_alternative_cabinet", "named_alternative", "specimen preservation", "the sample custodian", (
            "place specimens in Cabinet Quartz", "place specimens in Cabinet Granite", "place specimens in Cabinet Basalt",
        ), "keep specimens in Cabinet Granite"),
        b.obligation_case("fresh_alternative_radio", "named_alternative", "the tunnel drill", "the radio dispatcher", (
            "transmit updates on Channel Falcon", "transmit updates on Channel Heron", "transmit updates on Channel Osprey",
        ), "send updates on Channel Heron"),
        b.directed_case("fresh_roles_maple", "subject_object_role", "credential exchange", "enables", "Maple", "Oak", "Pine", "enables", "is enabled by"),
        b.directed_case("fresh_roles_ruby", "subject_object_role", "session exchange", "enables", "Ruby", "Sapphire", "Emerald", "enables", "is enabled by"),
        b.directed_case("fresh_roles_iris", "subject_object_role", "access exchange", "enables", "Iris", "Lily", "Rose", "enables", "is enabled by"),
        b.directed_case("fresh_cause_heat", "causal_reversal", "the bearing trial", "causes", "bearing friction", "local heating", "shaft vibration", "causes", "results from"),
        b.directed_case("fresh_cause_leak", "causal_reversal", "the pipe trial", "causes", "seal rupture", "fluid leakage", "pressure oscillation", "causes", "results from"),
        b.directed_case("fresh_cause_power", "causal_reversal", "the supply trial", "causes", "power loss", "fan shutdown", "controller reset", "causes", "results from"),
        b.directed_case("fresh_order_inspection", "temporal_order_reversal", "the pavement sequence", "precedes", "subgrade inspection", "asphalt placement", "line marking", "precedes", "follows"),
        b.directed_case("fresh_order_weld", "temporal_order_reversal", "the fabrication sequence", "precedes", "joint cleaning", "welding", "radiographic testing", "precedes", "follows"),
        b.directed_case("fresh_order_coat", "temporal_order_reversal", "the coating sequence", "precedes", "surface drying", "primer application", "finish coating", "precedes", "follows"),
        b.authority_case("fresh_authority_access", "the roof access review", ("the facilities manager", "the fire engineer", "the building owner"), "authorising roof access", "approving roof access"),
        b.authority_case("fresh_authority_test", "the test release", ("the laboratory director", "the inspection coordinator", "the client representative"), "approving the test procedure", "authorising the test procedure"),
        b.authority_case("fresh_authority_close", "the road closure review", ("the traffic engineer", "the police commander", "the council officer"), "authorising the road closure", "approving the road closure"),
        b.comparator_case("fresh_threshold_pressure", "the compressor trial", "the compressor attendant", (
            "vent the chamber when pressure exceeds 250 kilopascals", "vent the chamber when pressure falls below 250 kilopascals", "vent the chamber when pressure equals 250 kilopascals",
        ), "release chamber air whenever pressure is lower than 250 kilopascals"),
        b.comparator_case("fresh_threshold_cold", "the freezer trial", "the cold-room attendant", (
            "activate the heater when temperature exceeds -5 degrees Celsius", "activate the heater when temperature falls below -5 degrees Celsius", "activate the heater when temperature equals -5 degrees Celsius",
        ), "switch on the heater whenever temperature is lower than minus five degrees Celsius"),
        b.comparator_case("fresh_threshold_speed", "the ventilation trial", "the ventilation attendant", (
            "close the damper when airflow exceeds 22 metres per second", "close the damper when airflow falls below 22 metres per second", "close the damper when airflow equals 22 metres per second",
        ), "shut the damper whenever airflow is lower than 22 metres per second"),
        b.permission_case("fresh_condition_clearance", "shaft inspection", "the shaft crew", "enter the shaft", (
            "only if Clearance Cedar is valid", "even if Clearance Cedar is valid", "without Clearance Cedar being valid",
        ), "even if Clearance Cedar is valid"),
        b.permission_case("fresh_condition_interlock", "motor commissioning", "the motor crew", "start the motor", (
            "only after the interlock engages", "even after the interlock engages", "before the interlock engages",
        ), "even after the interlock engages"),
        b.permission_case("fresh_condition_license", "plant handover", "the acceptance team", "complete acceptance", (
            "only with the operating licence", "even with the operating licence", "without the operating licence",
        ), "even with the operating licence"),
    )
