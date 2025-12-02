from mable.cargo_bidding import TradingCompany, Bid

class Company12(TradingCompany):
    def __init__(self, fleet, name):
        super().__init__(fleet, name)
        self._future_trades = None
        self._planned_schedules = {}

    def pre_inform(self, trades, time):
        print(f"pre_inform called: storing {len(trades)} upcoming trades for time {time}")
        self._future_trades = trades

    def try_schedule_on_vessel(self, vessel, trade):
        try:
            new_schedule = vessel.schedule.copy()
            new_schedule.add_transportation(trade)

            if new_schedule.verify_schedule():
                return True, new_schedule

            print(
                f"Schedule not feasible for vessel {vessel.name} "
                f"with trade {getattr(trade, 'id', 'unknown')}."
            )
            return False, None

        except Exception as e:
            print(f"Exception while trying schedule on vessel {vessel.name}: {e}")
            return False, None

    def plan_for_trade(self, trade):
        for vessel in self._fleet:
            feasible, sched = self.try_schedule_on_vessel(vessel, trade)
            if feasible:
                return vessel, sched

        print(
            f"No feasible vessel found for trade "
            f"{getattr(trade, 'id', 'unknown')} – will NOT bid on this trade."
        )
        return None, None

    # ---------- NEW: margin logic ----------
    def _compute_margin(self, trade):
        """Choose a profit margin based on trade characteristics."""
        amount = float(getattr(trade, "amount", 0.0))

        # base margin
        margin = 1.5

        # large cargoes: more risk / fuel / time → slightly higher margin
        if amount > 70000:
            margin += 0.3
        # small cargoes: we can be a bit more aggressive on price
        elif amount < 30000:
            margin -= 0.2

        # never go below a minimal safety margin
        margin = max(margin, 1.05)

        print(f"Computed margin {margin:.2f} for amount={amount:.1f}")
        return margin
    # --------------------------------------

    def inform(self, trades, *args, **kwargs):
        print(f"\ninform called: {len(trades)} trades offered this round")
        bids = []
        self._planned_schedules = {}

        for i, trade in enumerate(trades):
            try:
                origin = getattr(trade, "origin_port", getattr(trade, "start_port", None))
                destination = getattr(trade, "destination_port", getattr(trade, "end_port", None))

                print(
                    f"Trade {i}: origin={getattr(origin, 'name', origin)}, "
                    f"dest={getattr(destination, 'name', destination)}, "
                    f"amount={getattr(trade, 'amount', 'NA')}"
                )

                vessel, sched = self.plan_for_trade(trade)
                if vessel is None or sched is None:
                    continue

                self._planned_schedules[trade] = (vessel, sched)

                cost = self.predict_cost(vessel, trade)
                margin = self._compute_margin(trade)
                bid_amount = cost * margin

                bids.append(Bid(amount=bid_amount, trade=trade))
                print(
                    f"Trade {i}: vessel={vessel.name}, "
                    f"bid={bid_amount:.2f}, cost_estimate={cost:.2f}, margin={margin:.2f}"
                )

            except Exception as e:
                print(f"Failed to process trade {i}: {e}")

        print(f"Total bids prepared: {len(bids)}")
        return bids

    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        print(f"\nreceive called: {len(contracts)} contracts won")

        for i, contract in enumerate(contracts):
            trade = contract.trade
            planned = self._planned_schedules.get(trade, None)

            if planned is None:
                print(
                    f"No stored plan for trade {getattr(trade, 'id', 'unknown')} "
                    f"in receive(); recomputing schedule."
                )
                vessel, sched = self.plan_for_trade(trade)
                if vessel is None or sched is None:
                    print(
                        f"Even recomputed schedule is infeasible for trade "
                        f"{getattr(trade, 'id', 'unknown')}. Leaving it unscheduled."
                    )
                    continue
            else:
                vessel, sched = planned

            try:
                if not sched.verify_schedule():
                    print(
                        f"Planned schedule for trade {getattr(trade, 'id', 'unknown')} "
                        f"failed verify_schedule() in receive(). Skipping."
                    )
                    continue

                print(
                    f"Applying schedule for trade {getattr(trade, 'id', 'unknown')} "
                    f"to vessel {vessel.name}"
                )
                vessel.schedule = sched

            except Exception as e:
                print(
                    f"Exception while applying schedule for trade "
                    f"{getattr(trade, 'id', 'unknown')} on vessel {vessel.name}: {e}"
                )

        self._future_trades = None
    
    def predict_cost(self, vessel, trade):
        try:
            origin = getattr(trade, "origin_port", getattr(trade, "start_port", "UNKNOWN"))
            destination = getattr(trade, "destination_port", getattr(trade, "end_port", "UNKNOWN"))
            origin_name = getattr(origin, "name", origin)
            dest_name = getattr(destination, "name", destination)

            amount = float(getattr(trade, "amount", 0.0))

            # Simple cost model:
            # - base component (crew, fixed costs)
            # - variable component scaling with cargo amount
            base_cost = 500.0
            variable_per_unit = 0.06
            variable_cost = variable_per_unit * amount

            total_cost = base_cost + variable_cost

            print(
                f"[cost] {origin_name} -> {dest_name}, "
                f"amount={amount:.1f}, base={base_cost:.1f}, "
                f"variable={variable_cost:.1f}, total={total_cost:.1f}"
            )
            return total_cost

        except Exception as e:
            print(f"[cost] Failed to estimate cost: {e}")
            # Large fallback so we don't accidentally bid very low when we have no idea
            return 10_000.0



# Notes:
# getattr is used to prevent crashing and null errors
# verbose is used to debug the code in terminal

# Places to improve:
# 1. bid_amount
# 2. predict_cost
# 3. plan_for_trade
# 4. pre_inform(use the future_trade concept)


