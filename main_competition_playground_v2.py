# main_competition_playground_v2.py
from mable.examples import environment, fleets, companies
import group12


def make_fleet(kind: str):
    k = (kind or "").lower()

    if k == "balanced":
        return fleets.mixed_fleet(num_suezmax=1, num_aframax=1, num_vlcc=1)

    if k == "small":
        return fleets.mixed_fleet(num_suezmax=0, num_aframax=3, num_vlcc=0)

    if k == "medium":
        return fleets.mixed_fleet(num_suezmax=3, num_aframax=0, num_vlcc=0)

    if k == "large":
        return fleets.mixed_fleet(num_suezmax=0, num_aframax=0, num_vlcc=3)

    return fleets.mixed_fleet(num_suezmax=1, num_aframax=1, num_vlcc=1)


def add_company(builder, cls, fleet_kind, label, **kwargs):
    fleet_obj = make_fleet(fleet_kind)  # IMPORTANT: new fleet instance per company
    builder.add_company(cls.Data(cls, fleet_obj, label, **kwargs))


def name_sim(sim, scenario_name, trades_per_month, months, run_id):
    try:
        sim.name = f"{scenario_name}|tpm={trades_per_month}|months={months}|run={run_id}"
    except Exception:
        pass


def build_balanced_setups(trades_per_month, months, scenario_name, run_id):
    builder = environment.get_specification_builder(
        trades_per_occurrence=trades_per_month,
        num_auctions=months
    )

    if scenario_name == "SmallVesselsFleet":
        kind = "small"
    elif scenario_name == "MediumVesselsFleet":
        kind = "medium"
    elif scenario_name == "LargeVesselsFleet":
        kind = "large"
    else:
        kind = "balanced"

    add_company(builder, group12.Company12, kind, "Company12")

    add_company(builder, companies.MyArchEnemy, kind, "Arch Enemy Aggressive", profit_factor=1.10)
    add_company(builder, companies.MyArchEnemy, kind, "Arch Enemy Standard", profit_factor=1.50)
    add_company(builder, companies.MyArchEnemy, kind, "Arch Enemy Premium", profit_factor=1.90)
    add_company(builder, companies.TheScheduler, kind, "Scheduler Standard", profit_factor=1.30)

    for cls_name in ("RandomCompany", "GreedyCompany", "CheapestCompany"):
        opp = getattr(companies, cls_name, None)
        if opp is not None:
            add_company(builder, opp, kind, cls_name)
            break

    sim = environment.generate_simulation(
        builder,
        show_detailed_auction_outcome=True,
        global_agent_timeout=60
    )
    name_sim(sim, scenario_name, trades_per_month, months, run_id)
    sim.run()


def build_onebig(trades_per_month, months, scenario_name, run_id):
    builder = environment.get_specification_builder(
        trades_per_occurrence=trades_per_month,
        num_auctions=months
    )

    add_company(builder, group12.Company12, "balanced", "Company12")

    add_company(builder, companies.MyArchEnemy, "large", "Arch Enemy OneBig", profit_factor=1.40)
    add_company(builder, companies.MyArchEnemy, "small", "Arch Enemy Small", profit_factor=1.25)
    add_company(builder, companies.TheScheduler, "small", "Scheduler Small", profit_factor=1.25)
    add_company(builder, companies.MyArchEnemy, "balanced", "Arch Enemy Balanced", profit_factor=1.60)

    sim = environment.generate_simulation(
        builder,
        show_detailed_auction_outcome=True,
        global_agent_timeout=60
    )
    name_sim(sim, scenario_name, trades_per_month, months, run_id)
    sim.run()


def build_onesmall(trades_per_month, months, scenario_name, run_id):
    builder = environment.get_specification_builder(
        trades_per_occurrence=trades_per_month,
        num_auctions=months
    )

    add_company(builder, group12.Company12, "balanced", "Company12")

    add_company(builder, companies.MyArchEnemy, "small", "Arch Enemy OneSmall", profit_factor=1.20)
    add_company(builder, companies.MyArchEnemy, "large", "Arch Enemy Large", profit_factor=1.55)
    add_company(builder, companies.TheScheduler, "large", "Scheduler Large", profit_factor=1.30)
    add_company(builder, companies.MyArchEnemy, "balanced", "Arch Enemy Balanced", profit_factor=1.60)

    sim = environment.generate_simulation(
        builder,
        show_detailed_auction_outcome=True,
        global_agent_timeout=60
    )
    name_sim(sim, scenario_name, trades_per_month, months, run_id)
    sim.run()


def build_halfsplit(trades_per_month, months, scenario_name, run_id):
    builder = environment.get_specification_builder(
        trades_per_occurrence=trades_per_month,
        num_auctions=months
    )

    add_company(builder, group12.Company12, "balanced", "Company12")

    add_company(builder, companies.MyArchEnemy, "small", "Arch Enemy Small A", profit_factor=1.25)
    add_company(builder, companies.TheScheduler, "small", "Scheduler Small", profit_factor=1.25)

    add_company(builder, companies.MyArchEnemy, "large", "Arch Enemy Big A", profit_factor=1.45)
    add_company(builder, companies.MyArchEnemy, "large", "Arch Enemy Big B", profit_factor=1.55)

    sim = environment.generate_simulation(
        builder,
        show_detailed_auction_outcome=True,
        global_agent_timeout=60
    )
    name_sim(sim, scenario_name, trades_per_month, months, run_id)
    sim.run()


def run_suite():
    months = 8
    trade_volumes = [20, 60, 100, 140]
    runs_per_setting = 3

    scenarios = [
        "BalancedFleet",
        "SmallVesselsFleet",
        "MediumVesselsFleet",
        "LargeVesselsFleet",
        "OneBig",
        "OneSmall",
        "HalfSmallHalfBig",
    ]

    run_id = 0
    for scenario_name in scenarios:
        for tpm in trade_volumes:
            for _ in range(runs_per_setting):
                run_id += 1
                print("\n" + "=" * 80)
                print(f"RUN {run_id}: {scenario_name} | trades/month={tpm} | months={months}")
                print("=" * 80)

                if scenario_name == "OneBig":
                    build_onebig(tpm, months, scenario_name, run_id)
                elif scenario_name == "OneSmall":
                    build_onesmall(tpm, months, scenario_name, run_id)
                elif scenario_name == "HalfSmallHalfBig":
                    build_halfsplit(tpm, months, scenario_name, run_id)
                else:
                    build_balanced_setups(tpm, months, scenario_name, run_id)


if __name__ == "__main__":
    run_suite()
