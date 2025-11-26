from mable.cargo_bidding import TradingCompany, Bid

class Company12(TradingCompany):
    def __init__(self, fleet, name):
        super().__init__(fleet, name)
        self._future_trades = None
        self._planned_schedules = {}

    def pre_inform(self, trades, time):
        print(f"[pre_inform] {len(trades)} trades announced for time {time}")
        self._future_trades = trades

    def try_schedule_on_vessel(self, vessel, trade):
        try:
            new_schedule = vessel.schedule.copy()
            new_schedule.add_transportation(trade)

            if new_schedule.verify_schedule():
                return True, new_schedule

            print(
                f"[schedule] Infeasible for vessel {vessel.name} "
                f"with trade {getattr(trade, 'id', 'unknown')}"
            )
            return False, None

        except Exception as e:
            print(f"[schedule] Error on vessel {vessel.name}: {e}")
            return False, None

    def plan_for_trade(self, trade):
        for vessel in self._fleet:
            ok, sched = self.try_schedule_on_vessel(vessel, trade)
            if ok:
                return vessel, sched

        print(
            f"[plan] No feasible vessel for trade {getattr(trade, 'id', 'unknown')}, skipping."
        )
        return None, None

    def inform(self, trades, *args, **kwargs):
        print(f"\n[inform] {len(trades)} trades in this auction")
        bids = []
        self._planned_schedules = {}

        for i, trade in enumerate(trades):
            try:
                origin = getattr(trade, "origin_port", getattr(trade, "start_port", None))
                destination = getattr(trade, "destination_port", getattr(trade, "end_port", None))

                print(
                    f"[trade {i}] origin={getattr(origin, 'name', origin)}, "
                    f"dest={getattr(destination, 'name', destination)}, "
                    f"amount={getattr(trade, 'amount', 'NA')}"
                )

                vessel, sched = self.plan_for_trade(trade)
                if vessel is None or sched is None:
                    continue

                self._planned_schedules[trade] = (vessel, sched)

                cost = self.predict_cost(vessel, trade)
                bid_amount = cost * 5
                bids.append(Bid(amount=bid_amount, trade=trade))

                print(
                    f"[bid] trade {i}, vessel={vessel.name}, "
                    f"bid={bid_amount:.2f}, cost_estimate={cost:.2f}"
                )

            except Exception as e:
                print(f"[inform] Failed to process trade {i}: {e}")

        print(f"[inform] Prepared {len(bids)} bids")
        return bids

    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        print(f"\n[receive] Won {len(contracts)} contracts")

        for i, contract in enumerate(contracts):
            trade = contract.trade
            planned = self._planned_schedules.get(trade)

            if planned is None:
                print(
                    f"[receive] No stored plan for trade {getattr(trade, 'id', 'unknown')}, "
                    f"recomputing."
                )
                vessel, sched = self.plan_for_trade(trade)
                if vessel is None or sched is None:
                    print(
                        f"[receive] Still infeasible for trade "
                        f"{getattr(trade, 'id', 'unknown')}, leaving unscheduled."
                    )
                    continue
            else:
                vessel, sched = planned

            try:
                if not sched.verify_schedule():
                    print(
                        f"[receive] Planned schedule for trade "
                        f"{getattr(trade, 'id', 'unknown')} failed verification, skipping."
                    )
                    continue

                print(
                    f"[receive] Applying schedule for trade {getattr(trade, 'id', 'unknown')} "
                    f"to vessel {vessel.name}"
                )
                vessel.schedule = sched

            except Exception as e:
                print(
                    f"[receive] Error applying schedule for trade "
                    f"{getattr(trade, 'id', 'unknown')} on vessel {vessel.name}: {e}"
                )

        self._future_trades = None

    def predict_cost(self, vessel, trade):
        try:
            origin = getattr(trade, "origin_port", getattr(trade, "start_port", "UNKNOWN"))
            destination = getattr(trade, "destination_port", getattr(trade, "end_port", "UNKNOWN"))
            origin_name = getattr(origin, "name", origin)
            dest_name = getattr(destination, "name", destination)

            total_cost = 1000.0
            print(f"[cost] {origin_name} -> {dest_name}, estimated cost={total_cost:.2f}")
            return total_cost

        except Exception as e:
            print(f"[cost] Failed to estimate cost: {e}")
            return 10_000.0


# Notes:
# getattr is used to prevent crashing and null errors
# verbose is used to debug the code in terminal

# Places to improve:
# 1. bid_amount
# 2. predict_cost
# 3. plan_for_trade
# 4. pre_inform(use the future_trade concept)