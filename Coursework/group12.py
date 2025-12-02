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
        """Choose a profit margin based on trade size."""
        amount = float(getattr(trade, "amount", 0.0))

        # Start a bit higher than before
        margin = 1.6

        # Very large cargoes: more risk and time, ask for more money
        if amount > 70000:
            margin += 0.3        # -> ~1.9
        # Medium cargoes: still decent margin
        elif amount > 40000:
            margin += 0.1        # -> ~1.7
        # Small cargoes: we can be slightly more competitive
        else:
            margin -= 0.1        # -> ~1.5

        # Never go below a minimal safety margin
        margin = max(margin, 1.15)

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
        """Rough cost estimate using cargo amount + distance (if available)."""
        try:
            origin = getattr(trade, "origin_port", getattr(trade, "start_port", "UNKNOWN"))
            destination = getattr(trade, "destination_port", getattr(trade, "end_port", "UNKNOWN"))
            origin_name = getattr(origin, "name", origin)
            dest_name = getattr(destination, "name", destination)

            amount = float(getattr(trade, "amount", 0.0))

            # ---- estimate distance in nautical miles if possible ----
            distance_nm = None
            if origin not in (None, "UNKNOWN") and destination not in (None, "UNKNOWN"):
                for method_name in ["distance", "distance_to", "great_circle_distance"]:
                    func = getattr(origin, method_name, None)
                    if callable(func):
                        try:
                            distance_nm = float(func(destination))
                            break
                        except Exception:
                            pass

            # If we failed to get distance from the API, fall back to something simple
            if distance_nm is None:
                distance_nm = 0.0

            # ---- cost model ----
            # base: crew / fixed ops
            base_cost = 500.0

            # scales with cargo amount
            variable_per_unit = 0.05   # tuned roughly from your previous runs
            variable_cost = variable_per_unit * amount

            # scales with distance (fuel, time at sea)
            # if distance is 0 (unknown), this just becomes 0
            distance_rate = 0.3        # cost per nautical mile
            distance_cost = distance_rate * distance_nm

            total_cost = base_cost + variable_cost + distance_cost

            print(
                f"[cost] {origin_name} -> {dest_name}, "
                f"amount={amount:.1f}, dist_nm={distance_nm:.1f}, "
                f"base={base_cost:.1f}, var={variable_cost:.1f}, "
                f"dist_cost={distance_cost:.1f}, total={total_cost:.1f}"
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


